import json
import logging
from src.services.platform_client import PlatformClient

logger = logging.getLogger(__name__)


async def chat_for_profile(
    platform: PlatformClient,
    system_prompt: str,
    conversation: list[dict],
) -> dict:
    """One turn of profiling dialogue.

    Returns dict with:
    - action: "reply" (continue dialog) or "profile" (profile extracted)
    - message: reply text (if action=reply)
    - interests, goals, summary: extracted profile (if action=profile)
    - company, position, business_objectives: business fields (if business)
    """
    content = ""
    try:
        messages = [{"role": "system", "content": system_prompt}] + conversation

        resp = await platform.chat_completion(
            messages=messages,
            response_format={"type": "json_object"},
        )

        content = resp["choices"][0]["message"]["content"]
        result = json.loads(content)

        if "action" not in result:
            result["action"] = "reply"
            result["message"] = content

        return result
    except json.JSONDecodeError:
        logger.warning("Profiling LLM returned non-JSON, treating as reply")
        return {"action": "reply", "message": content if content else "Расскажите подробнее о ваших интересах."}
    except Exception as e:
        logger.error("Profiling failed: %s", e)
        return {"action": "reply", "message": "Расскажите подробнее о ваших интересах."}


def normalize_profile_display(
    interests: list[str],
    goals: list[str],
    summary: str,
) -> tuple[list[str], str]:
    """Clean up LLM-extracted profile for user-facing display.

    - Dedupe interests; drop a bare parent tag ("CV") when subtags
      ("CV (детекция объектов)") are present — the parent adds noise.
    - Strip summary lines that merely repeat a goal ("Цель: ...") since
      goals are rendered separately.
    """
    # Dedupe preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in interests:
        t = tag.strip()
        if t and t not in seen:
            seen.add(t)
            deduped.append(t)

    # Drop bare parents that have subtags like "Parent (...)"
    parents_with_subtags = {
        t.split("(")[0].strip() for t in deduped if "(" in t
    }
    cleaned_interests = [
        t for t in deduped
        if not ("(" not in t and t in parents_with_subtags)
    ]

    # Strip goal-duplicating lines from summary
    goal_set = {g.strip().lower() for g in goals}
    kept_lines: list[str] = []
    for line in (summary or "").splitlines():
        stripped = line.strip()
        body = stripped
        for prefix in ("Цель:", "Цели:", "Goal:", "Goals:"):
            if body.startswith(prefix):
                body = body[len(prefix):].strip()
                break
        if stripped and body.lower() in goal_set:
            continue
        kept_lines.append(line)
    clean_summary = "\n".join(kept_lines).strip()

    return cleaned_interests, clean_summary


def build_profile_text(
    selected_tags: list[str] | None,
    keywords: list[str] | None,
    nl_summary: str | None,
    company: str | None = None,
    business_objectives: list[str] | None = None,
    raw_text: str | None = None,
) -> str:
    """Build text for embedding from profile data."""
    parts: list[str] = []
    if nl_summary:
        parts.append(nl_summary)
    if selected_tags:
        parts.append(f"Интересы: {', '.join(selected_tags)}")
    if keywords:
        parts.append(f"Ключевые слова: {', '.join(keywords)}")
    if company:
        parts.append(f"Компания: {company}")
    if business_objectives:
        parts.append(f"Бизнес-цели: {', '.join(business_objectives)}")
    if raw_text:
        parts.append(raw_text[:500])

    return ". ".join(parts) if parts else "Интерес к AI проектам"
