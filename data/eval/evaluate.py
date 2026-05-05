"""Standalone evaluation: IDF + LLM re-ranking vs expert annotations.

Reads golden_sample_expert.csv and projects_final.json, reproduces the
recommendation pipeline, and computes IR metrics against expert relevance.

Usage:
    python data/eval/evaluate.py              # full run with LLM
    python data/eval/evaluate.py --no-llm     # IDF-only baseline
    python data/eval/evaluate.py --verbose     # per-project scoring details
    python data/eval/evaluate.py --model anthropic/claude-sonnet-4-20250514
"""

import argparse
import csv
import json
import logging
import math
import os
import time
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECTS_FILE = DATA_DIR / "projects_final.json"
GOLDEN_CSV = SCRIPT_DIR / "golden_sample_expert.csv"
PREDICTIONS_FILE = SCRIPT_DIR / "system_predictions.json"
BACKEND_ENV = DATA_DIR.parent / "backend" / ".env"

logger = logging.getLogger("evaluate")

# ---------------------------------------------------------------------------
# Stop-words (mirrors profiling_service.py)
# ---------------------------------------------------------------------------
_STOP_WORDS = frozenset({
    "это", "как", "для", "что", "при", "все", "его", "она", "они", "так",
    "уже", "или", "если", "есть", "был", "они", "мне", "мой", "моя", "наш",
    "ваш", "где", "кто", "чем", "без", "под", "над", "про", "еще", "тоже",
    "очень", "будет", "можно", "нужно", "этот", "этом", "того", "тому",
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "not",
})

# ---------------------------------------------------------------------------
# LLM prompts (mirrors profiling_service.py)
# ---------------------------------------------------------------------------
RERANK_SYSTEM = (
    "Ты AI-ассистент для Demo Day. Перед тобой профиль гостя и проекты-кандидаты.\n"
    "Отранжируй проекты по релевантности к профилю гостя. Учитывай не только теги, "
    "но и ключевые слова из свободного текста.\n"
    "Верни JSON строго в формате:\n"
    '{"ranked": [{"project_id": "...", "score": 0.95}, ...]}\n'
    "Верни все проекты из входного списка, от наиболее к наименее релевантному."
)


# ===================================================================
# 1. Data loading
# ===================================================================

def load_projects() -> dict[int, dict]:
    """Load projects_final.json → {index: {title, description, author, tags}}."""
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    projects: dict[int, dict] = {}
    for i, p in enumerate(raw):
        title = (p.get("title") or "").strip()
        if not title or len(title) < 3:
            continue
        tags_raw = p.get("tags") or ""
        tags = [t.strip() for t in tags_raw.split(";") if t.strip()]
        if not tags:
            continue
        projects[i] = {
            "index": i,
            "title": title,
            "description": (p.get("description") or "").strip(),
            "author": (p.get("author") or "").strip() or "Неизвестен",
            "tags": tags,
        }
    return projects


def load_golden_sample(golden_path: Path | None = None) -> dict[str, dict]:
    """Parse golden_sample_expert.csv → {persona_id: {profile, relevance_map}}.

    Returns per persona:
        selected_tags: list[str]
        raw_text: str
        free_text_raw: str
        role, subtype, objective, ...
        relevance: {project_index: expert_relevance}
    """
    path = golden_path or GOLDEN_CSV
    personas: dict[str, dict] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["persona_id"]
            if pid not in personas:
                personas[pid] = {
                    "persona_id": pid,
                    "role": row["role"],
                    "subtype": row.get("subtype", ""),
                    "name": row["name"],
                    "selected_tags": [
                        t.strip()
                        for t in row["selected_tags"].split(";")
                        if t.strip()
                    ],
                    "raw_text": row.get("raw_text", ""),
                    "free_text_raw": row.get("free_text_raw", ""),
                    "objective": row.get("objective", ""),
                    "industries": row.get("industries", ""),
                    "tech_stack": row.get("tech_stack", ""),
                    "project_stages": row.get("project_stages", ""),
                    "collaboration_format": row.get("collaboration_format", ""),
                    "relevance": {},
                }
            idx = int(row["project_index"])
            rel = int(row["expert_relevance"])
            personas[pid]["relevance"][idx] = rel
    return personas


# ===================================================================
# 2. IDF scoring (mirrors profiling_service.py:compute_project_idf)
# ===================================================================

def compute_idf(projects: dict[int, dict]) -> dict[str, float]:
    """IDF = log(total / projects_with_tag) per tag."""
    total = len(projects)
    tag_counts: dict[str, int] = {}
    for p in projects.values():
        for tag in set(p["tags"]):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return {tag: math.log(total / max(cnt, 1)) for tag, cnt in tag_counts.items()}


# ===================================================================
# 3. Text search boost (simplified _text_search_scores)
# ===================================================================

def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from free text."""
    if not text:
        return []
    words = text.split()
    keywords: list[str] = []
    for w in words:
        cleaned = w.strip(".,;:!?\"'()[]{}").lower()
        if len(cleaned) > 3 and cleaned not in _STOP_WORDS and cleaned not in keywords:
            keywords.append(cleaned)
    return keywords[:20]


def text_search_scores(
    persona: dict, projects: dict[int, dict],
) -> dict[int, float]:
    """Count keyword matches in project title + description (case-insensitive).

    Mirrors _text_search_scores: collects terms from raw_text, free_text_raw,
    and business context (industries, objective, collaboration_format).
    """
    raw = persona.get("raw_text", "") or ""
    free = persona.get("free_text_raw", "") or ""
    terms = _extract_keywords(raw + " " + free)

    # Business context terms (mirrors profiling_service.py:408-414)
    if persona.get("role") == "business":
        for field in ("industries", "objective", "collaboration_format"):
            val = persona.get(field, "") or ""
            for part in val.replace(";", " ").split():
                part = part.strip().lower()
                if len(part) > 3 and part not in _STOP_WORDS and part not in terms:
                    terms.append(part)
        terms = terms[:20]

    if not terms:
        return {}

    scores: dict[int, float] = {}
    for idx, p in projects.items():
        haystack = (p["title"] + " " + p["description"]).lower()
        hits = sum(1 for t in terms if t in haystack)
        if hits:
            scores[idx] = float(hits)
    return scores


# ===================================================================
# 4. Combined IDF + text scoring
# ===================================================================

def score_projects(
    persona: dict,
    projects: dict[int, dict],
    idf: dict[str, float],
    verbose: bool = False,
) -> list[tuple[int, float]]:
    """Score all projects by IDF tag overlap + text boost → sorted desc."""
    guest_tags = set(persona["selected_tags"])
    text_scores = text_search_scores(persona, projects)
    max_idf = max(idf.values()) if idf else 1.0

    combined: dict[int, float] = {}
    for idx, p in projects.items():
        project_tags = set(p["tags"])
        idf_score = sum(idf.get(tag, 1.0) for tag in guest_tags if tag in project_tags)
        text_boost = text_scores.get(idx, 0.0) * max_idf
        total = idf_score + text_boost
        if total > 0:
            combined[idx] = total

    max_score = max(combined.values()) if combined else 1.0
    if max_score == 0:
        max_score = 1.0

    scored = [
        (idx, round(score / max_score * 100, 1))
        for idx, score in combined.items()
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    if verbose:
        pid = persona["persona_id"]
        logger.info(
            "%s: %d projects scored, top-5: %s",
            pid,
            len(scored),
            [(idx, s) for idx, s in scored[:5]],
        )

    return scored


# ===================================================================
# 5. LLM re-ranking (mirrors profiling_service.py:llm_rerank_projects)
# ===================================================================

def _load_env() -> dict[str, str]:
    """Read backend/.env into a dict."""
    env: dict[str, str] = {}
    if BACKEND_ENV.exists():
        for line in BACKEND_ENV.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def llm_rerank(
    persona: dict,
    candidates: list[tuple[int, float]],
    projects: dict[int, dict],
    api_key: str,
    base_url: str,
    model: str,
    rich_business_context: bool = True,
    strip_tags: bool = False,
) -> list[tuple[int, float]]:
    """Call OpenRouter to re-rank top candidates. Fallback to IDF order."""
    if not candidates:
        return []

    projects_json = []
    for idx, _score in candidates:
        p = projects[idx]
        entry: dict = {
            "project_id": str(idx),
            "title": p["title"],
            "description": p["description"],
        }
        if not strip_tags:
            entry["tags"] = p["tags"]
        projects_json.append(entry)

    all_tags = persona["selected_tags"]
    raw = persona.get("raw_text", "") or ""
    free = persona.get("free_text_raw", "") or ""
    text = raw or free
    keywords = _extract_keywords(raw + " " + free)

    # Build extra business context
    extra_context = ""
    if persona.get("role") == "business" and rich_business_context:
        # Full context: objective, industries, tech_stack, collaboration, stages
        objective = persona.get("objective", "")
        if objective:
            extra_context += f', цель="{objective}"'
        industries = persona.get("industries", "")
        if industries:
            extra_context += f', индустрии="{industries}"'
        tech_stack = persona.get("tech_stack", "")
        if tech_stack:
            extra_context += f', стек="{tech_stack}"'
        collaboration = persona.get("collaboration_format", "")
        if collaboration:
            extra_context += f', формат={collaboration}'
        project_stages = persona.get("project_stages", "")
        if project_stages:
            extra_context += f', стадии="{project_stages}"'

    if strip_tags:
        user_prompt = (
            f"Профиль: ключевые слова={json.dumps(keywords, ensure_ascii=False)}, "
            f'текст="{text}"{extra_context}\n'
            f"Проекты: {json.dumps(projects_json, ensure_ascii=False)}"
        )
    else:
        user_prompt = (
            f"Профиль: теги={json.dumps(all_tags, ensure_ascii=False)}, "
            f"ключевые слова={json.dumps(keywords, ensure_ascii=False)}, "
            f'текст="{text}"{extra_context}\n'
            f"Проекты: {json.dumps(projects_json, ensure_ascii=False)}"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": RERANK_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
    }
    # Anthropic models don't support response_format via OpenRouter
    if not model.startswith("anthropic/"):
        payload["response_format"] = {"type": "json_object"}

    last_error = None
    for attempt in range(3):
        try:
            resp = httpx.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # Strip markdown code fences if present (e.g. Anthropic models)
            text_content = content.strip()
            if text_content.startswith("```"):
                lines = text_content.splitlines()
                # Remove first and last fence lines
                lines = [l for l in lines if not l.strip().startswith("```")]
                text_content = "\n".join(lines)
            result = json.loads(text_content)
            ranked = result.get("ranked", [])

            idx_to_orig = {str(idx): (idx, s) for idx, s in candidates}
            reordered: list[tuple[int, float]] = []
            for item in ranked:
                pid_str = item.get("project_id")
                if pid_str in idx_to_orig:
                    orig_idx, _ = idx_to_orig[pid_str]
                    reordered.append((orig_idx, float(item.get("score", 0.5))))

            seen = {idx for idx, _ in reordered}
            for idx, score in candidates:
                if idx not in seen:
                    reordered.append((idx, score))

            return reordered

        except httpx.HTTPStatusError as e:
            last_error = e
            body = e.response.text[:300] if e.response else ""
            logger.warning("LLM attempt %d/3 failed: %s | %s", attempt + 1, e, body)
        except Exception as e:
            last_error = e
            logger.warning("LLM attempt %d/3 failed: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))

    logger.warning("LLM re-ranking failed after 3 attempts: %s — using IDF order", last_error)
    return candidates


# ===================================================================
# 6. Metrics
# ===================================================================

def dcg_at_k(gains: list[float], k: int) -> float:
    """DCG@K = sum gain(i) / log2(i+2) for i in 0..k-1."""
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains[:k]))


def ndcg_at_k(predicted: list[int], relevance: dict[int, int], k: int) -> float:
    """NDCG@K with graded relevance."""
    gains = [float(relevance.get(idx, 0)) for idx in predicted[:k]]
    dcg = dcg_at_k(gains, k)

    ideal_gains = sorted(relevance.values(), reverse=True)
    idcg = dcg_at_k([float(g) for g in ideal_gains], k)

    return dcg / idcg if idcg > 0 else 0.0


def precision_at_k(predicted: list[int], relevant_set: set[int], k: int) -> float:
    """Precision@K (binary: relevant = expert_relevance >= 2)."""
    top_k = set(predicted[:k])
    return len(top_k & relevant_set) / k if k > 0 else 0.0


def recall_at_k(predicted: list[int], relevant_set: set[int], k: int) -> float:
    """Recall@K (binary: relevant = expert_relevance >= 2)."""
    if not relevant_set:
        return 0.0
    top_k = set(predicted[:k])
    return len(top_k & relevant_set) / len(relevant_set)


# ===================================================================
# 7. Main
# ===================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate recommendation pipeline")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM re-ranking")
    parser.add_argument("--model", type=str, default=None, help="Override OpenRouter model")
    parser.add_argument("--verbose", action="store_true", help="Print per-project details")
    parser.add_argument(
        "--baseline-llm", action="store_true",
        help="Use baseline LLM prompt (no business context) to compare with enriched version",
    )
    parser.add_argument(
        "--golden", type=str, default=None,
        help="Path to golden sample CSV (default: golden_sample_expert.csv)",
    )
    parser.add_argument(
        "--personas", type=str, default=None,
        help="Comma-separated persona IDs to evaluate (default: all)",
    )
    parser.add_argument(
        "--enrich-tags", type=str, default=None,
        help="JSON file with tag enrichment: {project_index: [extra_tags]}",
    )
    parser.add_argument(
        "--no-tags-in-llm", action="store_true",
        help="Strip tags from LLM prompt (keep IDF selection, but LLM sees only descriptions)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(name)s: %(message)s",
    )

    # --- Load data ---
    projects = load_projects()
    golden_path = Path(args.golden) if args.golden else None
    personas = load_golden_sample(golden_path)

    # --- Filter personas ---
    if args.personas:
        keep = {p.strip() for p in args.personas.split(",")}
        personas = {k: v for k, v in personas.items() if k in keep}

    # --- Enrich tags ---
    if args.enrich_tags:
        with open(args.enrich_tags, encoding="utf-8") as f:
            enrichment = json.load(f)
        for idx_str, extra_tags in enrichment.items():
            idx = int(idx_str)
            if idx in projects:
                existing = set(projects[idx]["tags"])
                projects[idx]["tags"] = list(existing | set(extra_tags))
    print(f"Loaded {len(projects)} projects, {len(personas)} personas\n")

    # --- IDF ---
    idf = compute_idf(projects)

    # --- LLM config ---
    use_llm = not args.no_llm
    api_key = ""
    base_url = "https://openrouter.ai/api/v1"
    model = args.model or "openai/gpt-4.1"

    if use_llm:
        env = _load_env()
        api_key = env.get("OPENROUTER_API_KEY", "")
        if not api_key:
            api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            print("WARNING: No OPENROUTER_API_KEY found, falling back to --no-llm\n")
            use_llm = False
        else:
            model = args.model or env.get("OPENROUTER_MODEL", model)

    rich_biz = not args.baseline_llm
    mode_label = f"IDF + LLM ({model})" if use_llm else "IDF-only"
    if use_llm and not rich_biz:
        mode_label += " [baseline prompt]"
    elif use_llm:
        mode_label += " [+ business context]"
    print(f"Mode: {mode_label}\n")

    # --- Run pipeline per persona ---
    all_predictions: dict[str, list[dict]] = {}
    all_metrics: list[dict] = []

    for pid, persona in personas.items():
        # 1. IDF + text scoring
        scored = score_projects(persona, projects, idf, verbose=args.verbose)

        # 2. LLM re-rank top-20
        top20 = scored[:20]
        if use_llm and top20:
            reranked = llm_rerank(
                persona, top20, projects, api_key, base_url, model,
                rich_business_context=rich_biz,
                strip_tags=getattr(args, 'no_tags_in_llm', False),
            )
        else:
            reranked = top20

        # 3. Take top-15
        top15 = reranked[:15]
        predicted_indices = [idx for idx, _ in top15]

        # Save predictions
        all_predictions[pid] = [
            {
                "rank": rank + 1,
                "project_index": idx,
                "title": projects[idx]["title"],
                "score": round(score, 3),
            }
            for rank, (idx, score) in enumerate(top15)
        ]

        # 4. Compute metrics
        relevance = persona["relevance"]
        relevant_set = {idx for idx, rel in relevance.items() if rel >= 2}

        metrics = {
            "persona_id": pid,
            "name": persona["name"],
            "ndcg@5": round(ndcg_at_k(predicted_indices, relevance, 5), 4),
            "ndcg@15": round(ndcg_at_k(predicted_indices, relevance, 15), 4),
            "p@5": round(precision_at_k(predicted_indices, relevant_set, 5), 4),
            "p@15": round(precision_at_k(predicted_indices, relevant_set, 15), 4),
            "r@5": round(recall_at_k(predicted_indices, relevant_set, 5), 4),
            "r@15": round(recall_at_k(predicted_indices, relevant_set, 15), 4),
        }
        all_metrics.append(metrics)

    # --- Print table ---
    header = f"{'Persona':<42s} {'NDCG@5':>7s} {'NDCG@15':>8s} {'P@5':>6s} {'P@15':>6s} {'R@5':>6s} {'R@15':>6s}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for m in all_metrics:
        print(
            f"{m['name']:<42s} {m['ndcg@5']:>7.4f} {m['ndcg@15']:>8.4f} "
            f"{m['p@5']:>6.4f} {m['p@15']:>6.4f} {m['r@5']:>6.4f} {m['r@15']:>6.4f}"
        )

    # Aggregate
    n = len(all_metrics)
    agg = {
        k: round(sum(m[k] for m in all_metrics) / n, 4)
        for k in ("ndcg@5", "ndcg@15", "p@5", "p@15", "r@5", "r@15")
    }
    print(sep)
    print(
        f"{'AVERAGE':<42s} {agg['ndcg@5']:>7.4f} {agg['ndcg@15']:>8.4f} "
        f"{agg['p@5']:>6.4f} {agg['p@15']:>6.4f} {agg['r@5']:>6.4f} {agg['r@15']:>6.4f}"
    )
    print(sep)

    # --- Save predictions ---
    with open(PREDICTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_predictions, f, ensure_ascii=False, indent=2)
    print(f"\nPredictions saved to {PREDICTIONS_FILE}")


if __name__ == "__main__":
    main()
