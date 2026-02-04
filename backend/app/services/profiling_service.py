"""Guest profiling and recommendation service (EPIC-005)."""

import json
import logging
import math
import uuid

import sqlalchemy as sa
from sqlalchemy import delete, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clustering_run import ClusteringRun
from app.models.guest_profile import GuestProfile
from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.recommendation import Recommendation
from app.models.room import Room
from app.models.room_project import RoomProject
from app.models.tag import Tag
from app.services import llm_client

logger = logging.getLogger(__name__)

# --- LLM Prompts ---

TEXT_EXTRACTION_SYSTEM = """Ты AI-ассистент для Demo Day. Проанализируй текст гостя и извлеки интересы.
Допустимые теги: {tag_list}
Верни JSON строго в формате:
{{"tags": ["tag1", "tag2"], "keywords": ["keyword1", "keyword2"]}}
tags — только из списка допустимых. keywords — дополнительные ключевые слова не из списка."""

RERANK_SYSTEM = """Ты AI-ассистент для Demo Day. Перед тобой профиль гостя и проекты-кандидаты.
Отранжируй проекты по релевантности к профилю гостя. Учитывай не только теги, но и ключевые слова из свободного текста.
Верни JSON строго в формате:
{{"ranked": [{{"project_id": "...", "score": 0.95}}, ...]}}
Верни все проекты из входного списка, от наиболее к наименее релевантному."""

SUMMARY_SYSTEM = """Ты AI-ассистент для Demo Day. Сгенерируй краткое описание (2-3 предложения) каждого проекта, адаптированное под интересы гостя. Подчеркни аспекты релевантные для гостя.
Верни JSON строго в формате:
{{"summaries": [{{"project_id": "...", "summary": "..."}}, ...]}}"""


PROFILE_AGENT_SYSTEM = """Ты — AI-куратор Demo Day. Твоя задача — в диалоге выяснить интересы посетителя.

На Demo Day ~330 студенческих AI-проектов в нескольких залах. Стандартные теги проектов:
NLP, CV, LLM, Agents, EdTech, FinTech, MedTech, Security, ASR, TTS, Audio, Industrial, MLOps, RL, RecSys, Science, TimeSeries.

Расшифровка тегов:
- NLP (чат-боты, генерация текста, RAG, суммаризация)
- CV (детекция, сегментация, генерация изображений)
- LLM (большие языковые модели, файн-тюнинг, инференс)
- Agents (автономные агенты, мультиагентные системы, автоматизация)
- EdTech (образовательные платформы, адаптивное обучение)
- FinTech (антифрод, скоринг, трейдинг)
- MedTech (диагностика, анализ снимков, drug discovery)
- Security (детекция угроз, анализ вредоносного ПО)
- ASR (распознавание речи), TTS (синтез речи), Audio (обработка аудио)
- Industrial (предиктивное обслуживание, контроль качества)
- MLOps (деплой, мониторинг, пайплайны)
- RL (обучение с подкреплением)
- RecSys (рекомендательные системы, персонализация)
- Science (BioTech, natural sciences + ML)
- TimeSeries (прогнозирование временных рядов)

{selected_tags_block}

{role_context_block}

Формат ответа — СТРОГО JSON:
- Если нужно продолжить диалог:
  {{"action": "reply", "message": "твой ответ"}}
- Если информации достаточно и пора фиксировать профиль:
  {{"action": "profile", "interests": ["тег1", "тег2"], "goals": ["цель1"], "summary": "Краткое описание профиля"{partner_profile_fields}}}

interests должны содержать стандартные теги из списка выше + при необходимости уточняющие подтеги.

ВАЖНО: не торопись с action=profile. Сначала поговори, задай 1-2 вопроса. Переходи к profile только когда чётко понятны интересы."""


# --- Role-dependent context blocks ---

ROLE_CONTEXTS: dict[tuple[str, str | None], str] = {
    ("guest", "student"): (
        "Стиль общения: неформальный, на «ты», дружелюбный.\n"
        "Собеседник — студент. Выясни:\n"
        "- Какие технологии изучает или использует\n"
        "- Какие проекты хочет увидеть, что вдохновляет\n"
        "- Интересуют ли стажировки или карьерные возможности\n"
        "Правила:\n"
        "1. Отвечай коротко (2-4 предложения), по-русски, неформально\n"
        "2. Если уже выбраны теги — уточняй детали по ним\n"
        "3. Задавай вопросы про стек, проекты, что хочет увидеть\n"
        "4. Когда собрал достаточно (2-3 интереса) — предложи подвести итог"
    ),
    ("guest", "applicant"): (
        "Стиль общения: мотивирующий, на «ты», вдохновляющий.\n"
        "Собеседник — абитуриент, который только присматривается к AI. Выясни:\n"
        "- Какие области AI интересны (может не знать точных названий)\n"
        "- Какое карьерное направление привлекает\n"
        "- Уровень подготовки (школьник, первокурсник, самоучка)\n"
        "Правила:\n"
        "1. Отвечай коротко (2-4 предложения), по-русски, мотивирующе\n"
        "2. Если уже выбраны теги — объясни их простым языком\n"
        "3. Помоги сориентироваться в направлениях AI\n"
        "4. Когда собрал достаточно (2-3 интереса) — предложи подвести итог"
    ),
    ("guest", "other"): (
        "Стиль общения: профессиональный, на «вы», уважительный.\n"
        "Собеседник указал свою роль как: «{custom_subtype_text}». Адаптируй диалог под эту роль.\n"
        "Выясни:\n"
        "- Профессиональные интересы, связанные с AI\n"
        "- Что хочет найти на Demo Day\n"
        "- Какие проекты будут наиболее полезны\n"
        "Правила:\n"
        "1. Отвечай коротко (2-4 предложения), по-русски, на «вы»\n"
        "2. Если уже выбраны теги — уточняй детали по ним\n"
        "3. Задавай вопросы исходя из роли собеседника\n"
        "4. Когда собрал достаточно (2-3 интереса) — предложи подвести итог"
    ),
    ("business", None): (
        "Стиль общения: деловой, на «вы», профессиональный.\n"
        "Собеседник — бизнес-партнёр или потенциальный партнёр. Выясни:\n"
        "- Компанию и должность\n"
        "- Текущий или потенциальный партнёр (уже работает с Хабом или впервые)\n"
        "- Бизнес-цели визита: инвестиции, найм, технологическое партнёрство, поиск решений\n"
        "- Индустрию и какие AI-технологии интересны\n"
        "Правила:\n"
        "1. Отвечай коротко (2-4 предложения), по-русски, на «вы», деловым тоном\n"
        "2. Если уже выбраны теги — уточняй бизнес-контекст по ним\n"
        "3. Обязательно спроси компанию и должность, если не указаны\n"
        "4. Когда собрал достаточно (компания + цели + интересы) — предложи подвести итог\n\n"
        "ВАЖНО: при action=profile добавь дополнительные поля:\n"
        '  "company": "название компании",\n'
        '  "position": "должность",\n'
        '  "partner_status": "current" или "potential",\n'
        '  "business_objectives": ["technology", "hiring", "investment", "partnership"]'
    ),
}

# Default fallback context (generic guest)
_DEFAULT_ROLE_CONTEXT = (
    "Стиль общения: дружелюбный, по-русски.\n"
    "Правила:\n"
    "1. Отвечай коротко (2-4 предложения), дружелюбно но без лишней воды\n"
    "2. Если уже выбраны теги — учитывай их, уточняй детали\n"
    "3. Задавай уточняющие вопросы: какая сфера, какие задачи, что ищет\n"
    "4. Когда собрал достаточно (2-3 интереса) — предложи подвести итог"
)


def _build_role_context(
    role_code: str | None,
    guest_subtype: str | None,
    custom_subtype: str | None,
) -> tuple[str, str]:
    """Build role context block and partner profile fields hint.

    Returns (role_context_block, partner_profile_fields).
    partner_profile_fields is a string to inject into JSON format hint for business role.
    """
    is_business = role_code == "business"
    partner_profile_fields = ""
    if is_business:
        partner_profile_fields = (
            ', "company": "...", "position": "...", '
            '"partner_status": "current|potential", '
            '"business_objectives": ["technology", "hiring", "investment", "partnership"]'
        )

    # Lookup context: business uses (business, None), guests use (guest, subtype)
    if is_business:
        ctx = ROLE_CONTEXTS.get(("business", None), _DEFAULT_ROLE_CONTEXT)
    else:
        ctx = ROLE_CONTEXTS.get(("guest", guest_subtype), _DEFAULT_ROLE_CONTEXT)

    # Substitute custom_subtype_text for "other" subtype
    if guest_subtype == "other" and custom_subtype:
        ctx = ctx.replace("{custom_subtype_text}", custom_subtype)
    else:
        ctx = ctx.replace("{custom_subtype_text}", "гость")

    return ctx, partner_profile_fields


async def chat_for_profile(
    conversation: list[dict],
    selected_tags: list[str] | None = None,
    role_code: str | None = None,
    guest_subtype: str | None = None,
    custom_subtype: str | None = None,
) -> dict:
    """Multi-turn conversational profile discovery.

    conversation: list of {"role": "user"|"assistant", "content": "..."} messages.
    selected_tags: tags user already picked via buttons (may be empty).
    role_code: "guest" or "business".
    guest_subtype: "student", "applicant", "other" (for guests).
    custom_subtype: free-text subtype when guest_subtype is "other".
    Returns dict with either:
      {"action": "reply", "message": "..."} — continue conversation
      {"action": "profile", "interests": [...], "goals": [...], "summary": "...", ...} — done
    """
    if selected_tags:
        tags_block = f"Посетитель уже выбрал теги: {', '.join(selected_tags)}. Учитывай это и уточняй детали по этим темам."
    else:
        tags_block = "Посетитель пока не выбрал теги. Помоги определиться."

    role_context_block, partner_profile_fields = _build_role_context(
        role_code, guest_subtype, custom_subtype,
    )

    system_prompt = PROFILE_AGENT_SYSTEM.format(
        selected_tags_block=tags_block,
        role_context_block=role_context_block,
        partner_profile_fields=partner_profile_fields,
    )

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=system_prompt,
            user_prompt="",
            messages=conversation,
            json_mode=True,
        )

        action = response.get("action", "reply")
        if action == "profile":
            logger.info("Profile agent: extracted profile interests=%s", response.get("interests"))
            result = {
                "action": "profile",
                "interests": response.get("interests", []),
                "goals": response.get("goals", []),
                "summary": response.get("summary", ""),
            }
            # Extract partner-specific fields for business role
            if role_code == "business":
                for key in ("company", "position", "partner_status", "business_objectives"):
                    if key in response:
                        result[key] = response[key]
            return result
        else:
            message = response.get("message", "Расскажите подробнее о ваших интересах.")
            logger.info("Profile agent: continuing conversation")
            return {"action": "reply", "message": message}

    except Exception:
        logger.warning("Profile agent LLM failed (graceful degradation)")
        return {"action": "reply", "message": "Расскажите, какие технологии или области AI вам интересны?"}


# --- T005: Helper functions ---


async def get_available_tags(
    session: AsyncSession, event_id: uuid.UUID
) -> list[tuple[str, int]]:
    """Get all tags used by projects in the event, with project count, sorted desc."""
    result = await session.execute(
        select(Tag.name, func.count(ProjectTag.project_id).label("cnt"))
        .join(ProjectTag, ProjectTag.tag_id == Tag.id)
        .join(Project, Project.id == ProjectTag.project_id)
        .where(Project.event_id == event_id)
        .group_by(Tag.name)
        .order_by(func.count(ProjectTag.project_id).desc())
    )
    return [(row.name, row.cnt) for row in result.all()]


async def get_or_create_profile(
    session: AsyncSession, user_id: uuid.UUID, event_id: uuid.UUID
) -> GuestProfile:
    """Get existing profile or create a new empty one."""
    result = await session.execute(
        select(GuestProfile)
        .where(GuestProfile.user_id == user_id)
        .where(GuestProfile.event_id == event_id)
    )
    profile = result.scalars().first()
    if profile:
        return profile

    profile = GuestProfile(
        user_id=user_id,
        event_id=event_id,
        selected_tags=[],
        extracted_tags=[],
        keywords=[],
    )
    session.add(profile)
    await session.flush()
    return profile


async def save_profile(
    session: AsyncSession,
    profile: GuestProfile,
    selected_tags: list[str],
    keywords: list[str],
    raw_text: str | None,
    extra_data: dict | None = None,
) -> GuestProfile:
    """Save/update profile fields. Deletes old recommendations on update."""
    profile.selected_tags = selected_tags
    profile.extracted_tags = []
    profile.keywords = keywords
    profile.raw_text = raw_text
    if extra_data is not None:
        profile.extra_data = extra_data

    await session.commit()
    logger.info("Profile saved: user=%s tags=%s keywords=%s extra_data=%s", profile.user_id, selected_tags, keywords, extra_data)
    return profile


# --- T006: Text extraction ---


async def extract_interests_from_text(
    raw_text: str, available_tags: list[str]
) -> dict:
    """Extract interests from free text using LLM. Graceful degradation on failure."""
    if not raw_text or not raw_text.strip():
        return {"tags": [], "keywords": []}

    tag_list_str = ", ".join(available_tags)
    system_prompt = TEXT_EXTRACTION_SYSTEM.format(tag_list=tag_list_str)

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=system_prompt,
            user_prompt=raw_text,
            json_mode=True,
        )

        tags = [t for t in response.get("tags", []) if t in available_tags]
        keywords = response.get("keywords", [])

        logger.info("Text extraction: tags=%s keywords=%s", tags, keywords)
        return {"tags": tags, "keywords": keywords}

    except Exception:
        logger.warning("LLM text extraction failed, returning empty (graceful degradation)")
        return {"tags": [], "keywords": []}


# --- T007: IDF computation ---


async def compute_project_idf(
    session: AsyncSession, event_id: uuid.UUID
) -> dict[str, float]:
    """Compute IDF weight for each tag: log(total_projects / projects_with_tag)."""
    total_result = await session.execute(
        select(func.count(func.distinct(ProjectTag.project_id)))
        .join(Project, Project.id == ProjectTag.project_id)
        .where(Project.event_id == event_id)
    )
    total_projects = total_result.scalar() or 1

    tag_counts_result = await session.execute(
        select(Tag.name, func.count(func.distinct(ProjectTag.project_id)))
        .join(ProjectTag, ProjectTag.tag_id == Tag.id)
        .join(Project, Project.id == ProjectTag.project_id)
        .where(Project.event_id == event_id)
        .group_by(Tag.name)
    )

    idf: dict[str, float] = {}
    for tag_name, count in tag_counts_result.all():
        idf[tag_name] = math.log(total_projects / max(count, 1))

    return idf


# --- T008: Score projects ---

# Russian stop-words for text search filtering
_STOP_WORDS = frozenset({
    "это", "как", "для", "что", "при", "все", "его", "она", "они", "так",
    "уже", "или", "если", "есть", "был", "они", "мне", "мой", "моя", "наш",
    "ваш", "где", "кто", "чем", "без", "под", "над", "про", "еще", "тоже",
    "очень", "будет", "можно", "нужно", "этот", "этом", "того", "тому",
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "not",
})


async def _text_search_scores(
    session: AsyncSession, event_id: uuid.UUID, profile: GuestProfile,
) -> dict[uuid.UUID, float]:
    """Score projects via PostgreSQL full-text search on keywords and raw_text.

    Returns {project_id: text_score} where score is a relative relevance value.
    """
    # Collect search terms from keywords + meaningful words from raw_text
    terms: list[str] = []
    if profile.keywords:
        terms.extend(profile.keywords)

    if profile.raw_text:
        words = profile.raw_text.split()
        for w in words:
            cleaned = w.strip(".,;:!?\"'()[]{}").lower()
            if len(cleaned) > 3 and cleaned not in _STOP_WORDS and cleaned not in terms:
                terms.append(cleaned)

    # Add business context terms
    if profile.extra_data:
        ed = profile.extra_data
        if ed.get("company"):
            terms.append(ed["company"])
        for obj in ed.get("business_objectives", []):
            if obj not in terms:
                terms.append(obj)

    # Limit to 20 terms
    terms = terms[:20]
    if not terms:
        return {}

    # Try PostgreSQL full-text search first
    query_parts = [t.replace("'", "''") for t in terms if t.strip()]
    if not query_parts:
        return {}

    tsquery_str = " | ".join(query_parts)
    scores: dict[uuid.UUID, float] = {}

    try:
        result = await session.execute(
            sa.text(
                "SELECT p.id, ts_rank("
                "  to_tsvector('russian', coalesce(p.title, '') || ' ' || coalesce(p.description, '')), "
                "  plainto_tsquery('russian', :query)"
                ") AS rank "
                "FROM projects p "
                "WHERE p.event_id = :eid "
                "AND to_tsvector('russian', coalesce(p.title, '') || ' ' || coalesce(p.description, '')) "
                "   @@ plainto_tsquery('russian', :query) "
                "ORDER BY rank DESC"
            ),
            {"query": " ".join(query_parts), "eid": event_id},
        )
        for row in result.all():
            scores[row[0]] = float(row[1])
    except Exception:
        logger.warning("FTS search failed, trying ILIKE fallback")

    # Fallback: if FTS gave no results, try ILIKE on keywords
    if not scores:
        try:
            for term in terms[:5]:
                pattern = f"%{term}%"
                result = await session.execute(
                    sa.text(
                        "SELECT id FROM projects "
                        "WHERE event_id = :eid "
                        "AND (title ILIKE :pat OR description ILIKE :pat)"
                    ),
                    {"eid": event_id, "pat": pattern},
                )
                for row in result.all():
                    scores[row[0]] = scores.get(row[0], 0.0) + 1.0
        except Exception:
            logger.warning("ILIKE fallback also failed")

    return scores


async def score_projects(
    session: AsyncSession, event_id: uuid.UUID, profile: GuestProfile
) -> list[tuple[uuid.UUID, float]]:
    """Score all projects by IDF tag overlap + text search, normalized to 0-100."""
    idf = await compute_project_idf(session, event_id)

    # All guest interest tags (deduplicated)
    all_tags = list(set(profile.selected_tags))

    # Text search scores
    text_scores = await _text_search_scores(session, event_id, profile)

    # If no tags AND no text matches, return empty
    if not all_tags and not text_scores:
        return []

    # Load all projects with their tags
    result = await session.execute(
        select(Project)
        .where(Project.event_id == event_id)
        .options(selectinload(Project.tags).selectinload(ProjectTag.tag))
    )
    projects = result.scalars().all()

    # Determine max IDF for scaling text boost
    max_idf = max(idf.values()) if idf else 1.0

    combined: dict[uuid.UUID, float] = {}
    for project in projects:
        project_tag_names = {pt.tag.name for pt in project.tags}
        idf_score = 0.0
        for tag in all_tags:
            if tag in project_tag_names:
                idf_score += idf.get(tag, 1.0)

        # Text boost scaled to IDF magnitude
        text_boost = text_scores.get(project.id, 0.0) * max_idf
        combined[project.id] = idf_score + text_boost

    # Normalize to 0-100
    max_score = max(combined.values()) if combined else 1.0
    if max_score == 0:
        max_score = 1.0

    scored: list[tuple[uuid.UUID, float]] = [
        (pid, round(score / max_score * 100, 1))
        for pid, score in combined.items()
        if score > 0
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# --- T009: LLM re-ranking ---


async def llm_rerank_projects(
    profile: GuestProfile,
    candidates: list[tuple[uuid.UUID, float, str, str, list[str]]],
) -> list[tuple[uuid.UUID, float]]:
    """LLM re-rank top candidates. Input: list of (project_id, score, title, description, tags).
    Returns reordered (project_id, score). Falls back to original order on failure."""
    if not candidates:
        return []

    all_tags = list(set(profile.selected_tags))
    projects_json = [
        {
            "project_id": str(pid),
            "title": title,
            "description": desc,
            "tags": tags,
        }
        for pid, _, title, desc, tags in candidates
    ]

    extra_context = ""
    if profile.extra_data:
        ed = profile.extra_data
        if ed.get("company"):
            extra_context += f', компания="{ed["company"]}"'
        if ed.get("business_objectives"):
            extra_context += f", бизнес-цели={json.dumps(ed['business_objectives'], ensure_ascii=False)}"

    user_prompt = (
        f"Профиль: теги={json.dumps(all_tags, ensure_ascii=False)}, "
        f"ключевые слова={json.dumps(profile.keywords, ensure_ascii=False)}, "
        f'текст="{profile.raw_text or ""}"{extra_context}\n'
        f"Проекты: {json.dumps(projects_json, ensure_ascii=False)}"
    )

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=RERANK_SYSTEM,
            user_prompt=user_prompt,
            json_mode=True,
        )

        ranked = response.get("ranked", [])
        # Build reordered list
        id_to_orig = {str(pid): (pid, score) for pid, score, *_ in candidates}
        reordered = []
        for item in ranked:
            pid_str = item.get("project_id")
            if pid_str in id_to_orig:
                orig_pid, _ = id_to_orig[pid_str]
                reordered.append((orig_pid, float(item.get("score", 0.5))))

        # Add any missing candidates at the end
        seen = {str(pid) for pid, _ in reordered}
        for pid, score, *_ in candidates:
            if str(pid) not in seen:
                reordered.append((pid, score))

        logger.info("LLM re-ranking completed: %d projects", len(reordered))
        return reordered

    except Exception:
        logger.warning("LLM re-ranking failed, using tag-only scores (graceful degradation)")
        return [(pid, score) for pid, score, *_ in candidates]


# --- T010: LLM summaries ---


async def generate_llm_summaries(
    profile: GuestProfile,
    projects: list[tuple[uuid.UUID, str, str, list[str]]],
) -> dict[uuid.UUID, str | None]:
    """Batch-generate 2-3 sentence summaries for projects adapted to guest profile.
    Input: list of (project_id, title, description, tags).
    Returns {project_id: summary or None}. Falls back to None on failure."""
    if not projects:
        return {}

    all_tags = list(set(profile.selected_tags))
    interests_data: dict = {"tags": all_tags, "keywords": profile.keywords}
    if profile.extra_data:
        ed = profile.extra_data
        if ed.get("company"):
            interests_data["company"] = ed["company"]
        if ed.get("business_objectives"):
            interests_data["business_objectives"] = ed["business_objectives"]

    guest_interests = json.dumps(interests_data, ensure_ascii=False)

    projects_text = "\n".join(
        f"- project_id: {pid}, title: {title}, tags: {tags}, description: {desc}"
        for pid, title, desc, tags in projects
    )

    user_prompt = f"Профиль гостя: {guest_interests}\n\nПроекты:\n{projects_text}"

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=SUMMARY_SYSTEM,
            user_prompt=user_prompt,
            json_mode=True,
        )

        summaries = {}
        for item in response.get("summaries", []):
            try:
                pid = uuid.UUID(item["project_id"])
                summaries[pid] = item.get("summary")
            except (ValueError, KeyError):
                continue

        logger.info("LLM summaries generated: %d/%d", len(summaries), len(projects))
        return summaries

    except Exception:
        logger.warning("LLM summary generation failed (graceful degradation)")
        return {pid: None for pid, *_ in projects}


# --- T011: Generate recommendations (orchestrator) ---


async def generate_recommendations(
    session: AsyncSession, profile: GuestProfile
) -> dict:
    """Orchestrate: IDF score → LLM rerank → LLM summaries → save recommendations."""
    import time

    start = time.monotonic()
    event_id = profile.event_id

    # 1. Score all projects by IDF tag overlap
    scored = await score_projects(session, event_id, profile)
    if not scored:
        logger.info("No scored projects, padding with all projects")

    # 2. Take top-20 candidates with project details for LLM
    top_ids = [pid for pid, _ in scored[:20]]
    if top_ids:
        result = await session.execute(
            select(Project)
            .where(Project.id.in_(top_ids))
            .options(selectinload(Project.tags).selectinload(ProjectTag.tag))
        )
        projects_map = {p.id: p for p in result.scalars().all()}
    else:
        projects_map = {}

    candidates = []
    for pid, score in scored[:20]:
        p = projects_map.get(pid)
        if p:
            tag_names = [pt.tag.name for pt in p.tags]
            candidates.append((p.id, score, p.title, p.description, tag_names))

    # 3. LLM re-rank top-20 → reordered
    if candidates:
        reranked = await llm_rerank_projects(profile, candidates)
    else:
        reranked = []

    # 4. Take top-15
    top15 = reranked[:15]

    # 5. Pad with popular projects if <10 (FR-013)
    if len(top15) < 10:
        existing_ids = {pid for pid, _ in top15}
        # Get popular projects not already included
        popular_result = await session.execute(
            select(Project.id)
            .where(Project.event_id == event_id)
            .where(Project.id.notin_(existing_ids) if existing_ids else true())
            .order_by(Project.created_at)
            .limit(10 - len(top15))
        )
        for row in popular_result.all():
            top15.append((row[0], 0.0))
        logger.info("Padded recommendations to %d with popular projects", len(top15))

    # 6. Load project details for top-15
    final_ids = [pid for pid, _ in top15]
    if final_ids:
        result = await session.execute(
            select(Project)
            .where(Project.id.in_(final_ids))
            .options(selectinload(Project.tags).selectinload(ProjectTag.tag))
        )
        final_projects = {p.id: p for p in result.scalars().all()}
    else:
        final_projects = {}

    # 7. Generate LLM summaries for top-15
    summary_input = []
    for pid, _ in top15:
        p = final_projects.get(pid)
        if p:
            tag_names = [pt.tag.name for pt in p.tags]
            summary_input.append((p.id, p.title, p.description, tag_names))

    summaries = await generate_llm_summaries(profile, summary_input)

    # 8. Normalize final scores to 0-100
    raw_scores = [s for _, s in top15]
    max_final = max(raw_scores) if raw_scores else 1.0
    if max_final <= 0:
        max_final = 1.0
    # If scores are already 0-100 scale (from score_projects), keep them;
    # if they're 0-1 scale (from LLM rerank), scale up.
    if max_final <= 1.0:
        top15 = [(pid, round(s * 100, 1)) for pid, s in top15]
    elif max_final > 100:
        top15 = [(pid, round(s / max_final * 100, 1)) for pid, s in top15]

    # 9. Delete old recommendations
    await session.execute(
        delete(Recommendation).where(Recommendation.guest_profile_id == profile.id)
    )

    # 10. Save new recommendations
    recs = []
    for rank_idx, (pid, score) in enumerate(top15):
        category = "must_visit" if rank_idx < 5 else "if_time"
        p = final_projects.get(pid)
        llm_summary = summaries.get(pid)

        # Fallback: first 2 sentences of description if no LLM summary
        if not llm_summary and p:
            sentences = p.description.split(".")
            llm_summary = ".".join(sentences[:2]).strip()
            if llm_summary and not llm_summary.endswith("."):
                llm_summary += "."

        rec = Recommendation(
            guest_profile_id=profile.id,
            project_id=pid,
            relevance_score=round(score, 3),
            category=category,
            rank=rank_idx + 1,
            llm_summary=llm_summary,
        )
        session.add(rec)
        recs.append(rec)

    await session.commit()

    elapsed = time.monotonic() - start
    logger.info(
        "Recommendations generated: %d projects in %.1fs (profile=%s)",
        len(recs), elapsed, profile.id,
    )

    return await get_recommendations(session, profile.id)


# --- T012: Get recommendations ---


async def get_recommendations(
    session: AsyncSession, profile_id: uuid.UUID
) -> dict | None:
    """Load existing recommendations with project details, split into categories."""
    result = await session.execute(
        select(Recommendation)
        .where(Recommendation.guest_profile_id == profile_id)
        .options(
            selectinload(Recommendation.project)
            .selectinload(Project.tags)
            .selectinload(ProjectTag.tag),
            selectinload(Recommendation.project)
            .selectinload(Project.room_assignments)
            .selectinload(RoomProject.room),
        )
        .order_by(Recommendation.rank)
    )
    recs = result.scalars().all()
    if not recs:
        return None

    # Collect room info for conflict detection
    project_rooms: dict[uuid.UUID, tuple[str | None, int | None]] = {}
    for rec in recs:
        p = rec.project
        room_name = None
        room_number = None
        for ra in p.room_assignments:
            room_name = ra.room.name
            room_number = ra.room.display_order + 1
            break
        project_rooms[p.id] = (room_name, room_number)

    # Detect room conflicts: projects in different rooms
    all_room_numbers = [rn for _, rn in project_rooms.values() if rn is not None]

    def get_conflict_rooms(pid: uuid.UUID) -> list[int]:
        _, my_room = project_rooms.get(pid, (None, None))
        if my_room is None:
            return []
        return sorted(set(rn for rn in all_room_numbers if rn != my_room))

    def format_rec(rec: Recommendation) -> dict:
        p = rec.project
        room_name, room_number = project_rooms.get(p.id, (None, None))
        return {
            "project_id": str(p.id),
            "rank": rec.rank,
            "title": p.title,
            "summary": rec.llm_summary or "",
            "tags": [pt.tag.name for pt in p.tags],
            "author": p.author,
            "room_name": room_name,
            "room_number": room_number,
            "relevance_score": rec.relevance_score,
            "conflict_rooms": get_conflict_rooms(p.id),
        }

    must_visit = [format_rec(r) for r in recs if r.category == "must_visit"]
    if_time = [format_rec(r) for r in recs if r.category == "if_time"]

    return {
        "profile_id": str(profile_id),
        "total": len(recs),
        "must_visit": must_visit,
        "if_time": if_time,
    }


# --- T013: Get project detail ---


async def get_project_detail(
    session: AsyncSession, profile_id: uuid.UUID, project_id: uuid.UUID
) -> dict | None:
    """Load full project detail for a project in guest's recommendation list."""
    result = await session.execute(
        select(Recommendation)
        .where(Recommendation.guest_profile_id == profile_id)
        .where(Recommendation.project_id == project_id)
        .options(
            selectinload(Recommendation.project)
            .selectinload(Project.tags)
            .selectinload(ProjectTag.tag),
            selectinload(Recommendation.project)
            .selectinload(Project.room_assignments)
            .selectinload(RoomProject.room),
        )
    )
    rec = result.scalars().first()
    if not rec:
        return None

    p = rec.project
    room_name = None
    room_number = None
    for ra in p.room_assignments:
        room_name = ra.room.name
        room_number = ra.room.display_order + 1
        break

    return {
        "id": str(p.id),
        "title": p.title,
        "description": p.description,
        "author": p.author,
        "telegram_contact": p.telegram_contact,
        "tags": [pt.tag.name for pt in p.tags],
        "room_name": room_name,
        "room_number": room_number,
        "relevance_score": rec.relevance_score,
        "llm_summary": rec.llm_summary,
    }
