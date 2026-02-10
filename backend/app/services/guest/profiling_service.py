# -*- coding: utf-8 -*-
"""Guest profiling and recommendation service (EPIC-005)."""

import json
import logging
import uuid

from sqlalchemy import delete, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.guest_profile import GuestProfile
from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.recommendation import Recommendation
from app.models.room_project import RoomProject
from app.models.tag import Tag
from app.services.core import llm_client

logger = logging.getLogger(__name__)

# --- LLM Prompts ---

TEXT_EXTRACTION_SYSTEM = """Ты AI-ассистент для Demo Day. Проанализируй текст гостя и извлеки интересы.
Допустимые теги: {tag_list}
Верни JSON строго в формате:
{{"tags": ["tag1", "tag2"], "keywords": ["keyword1", "keyword2"]}}
tags --только из списка допустимых. keywords --дополнительные ключевые слова не из списка."""

SUMMARY_SYSTEM = """Ты AI-ассистент для Demo Day. Сгенерируй краткое описание (2-3 предложения) каждого проекта, адаптированное под интересы гостя. Подчеркни аспекты релевантные для гостя.
Верни JSON строго в формате:
{{"summaries": [{{"project_id": "...", "summary": "..."}}, ...]}}"""


PROFILE_AGENT_SYSTEM = """Ты --AI-куратор Demo Day. Твоя задача --за 1-2 сообщения выяснить интересы посетителя и зафиксировать профиль.

На Demo Day ~330 студенческих AI-проектов в нескольких залах. Стандартные теги:
NLP (чат-боты, RAG, суммаризация), CV (детекция, сегментация, генерация картинок), LLM (файн-тюнинг, инференс), Agents (автономные агенты, мультиагентные системы), EdTech, FinTech (антифрод, скоринг), MedTech (диагностика, drug discovery), Security (детекция угроз), ASR (распознавание речи), TTS (синтез речи), Audio, Industrial (предиктивное обслуживание, контроль качества), MLOps, RL, RecSys, Science (BioTech), TimeSeries.

{selected_tags_block}

{role_context_block}

ФОРМАТ ОТВЕТА --строго JSON:
- Продолжить диалог: {{"action": "reply", "message": "..."}}
- Зафиксировать профиль: {{"action": "profile", "interests": ["тег1", "тег2"], "goals": ["цель1"], "summary": "Краткое описание профиля на русском, 1-2 предложения"{partner_profile_fields}}}

interests --стандартные теги из списка выше. Если пользователь описал узкую задачу, добавь уточняющий подтег: например "CV (industrial quality inspection)" или "NLP (юридические документы)".

КРИТИЧЕСКИЕ ПРАВИЛА ДИАЛОГА:
1. МАКСИМУМ 2 сообщения от тебя за весь диалог. Считай свои reply --после 2-го ОБЯЗАТЕЛЬНО action=profile.
2. ОБЯЗАТЕЛЬНО задай хотя бы ОДИН уточняющий вопрос перед финализацией профиля. Первое сообщение ВСЕГДА action=reply с вопросом, НЕ action=profile.
3. ОДИН вопрос за сообщение. Не перечисляй варианты списком. Максимум 2 альтернативы.
4. Отвечай 2-3 предложения. Не объясняй теги, если не спрашивают.
5. summary в profile --конкретное описание интересов, а не перечисление тегов.

===FEW-SHOT ПРИМЕРЫ===

Пример 1 (студент, есть теги NLP+Agents):
User: "Меня интересуют темы: NLP, Agents"
Assistant: {{"action": "reply", "message": "Хороший выбор! Уточни: тебе ближе чат-боты и RAG, или автономные агенты для автоматизации задач?"}}
User: "автономные агенты, хочу делать AI-ассистентов"
Assistant: {{"action": "profile", "interests": ["NLP", "Agents", "LLM"], "goals": ["Увидеть проекты AI-ассистентов"], "summary": "Студент, интересуется автономными AI-агентами и ассистентами на основе LLM. Хочет увидеть практические реализации."}}

Пример 2 (бизнес-партнёр, без тегов):
User: "Я из НЛМК, ищем CV-решения для контроля качества на производстве"
Assistant: {{"action": "reply", "message": "Понятно, промышленный CV --актуальная тема. Какая основная задача: классификация дефектов по фото или мониторинг процессов в реальном времени?"}}
User: "классификация дефектов, годен/брак по фото с камер"
Assistant: {{"action": "profile", "interests": ["CV", "Industrial"], "goals": ["Найти решение для контроля качества"], "summary": "НЛМК, ищут CV-решение для классификации дефектов (годен/брак) по фото с камер на производстве.", "company": "НЛМК", "position": "", "partner_status": "potential", "business_objectives": ["technology"]}}

Пример 3 (абитуриент, выбрал теги TTS+NLP+CV+Security):
User: "Меня интересуют темы: TTS, NLP, CV, Security"
Assistant: {{"action": "reply", "message": "Широкий набор! Что тебе ближе: создавать продукты для людей (голосовые ассистенты, контент) или защищать системы (поиск угроз, фрода)?"}}
User: "продукты для людей, голосовые ассистенты"
Assistant: {{"action": "profile", "interests": ["NLP", "TTS", "ASR", "CV"], "goals": ["Собрать голосового ассистента"], "summary": "Абитуриент, хочет создавать голосовых AI-ассистентов. Интересует связка ASR-NLP-TTS и компьютерное зрение для мультимодальности."}}
===КОНЕЦ ПРИМЕРОВ==="""


# --- Role-dependent context blocks ---

ROLE_CONTEXTS: dict[tuple[str, str | None], str] = {
    ("guest", "student"): (
        "Стиль: неформальный, на «ты», дружелюбный, по-русски.\n"
        "Собеседник --студент. Выясни: какие технологии/проекты интересны и зачем (вдохновение, стажировка, идеи для своего проекта).\n"
        "Стратегия: если теги уже есть --уточни конкретное применение (1 вопрос) → action=profile.\n"
        "Если тегов нет --спроси что изучает/чем увлекается → из ответа выведи теги → action=profile."
    ),
    ("guest", "applicant"): (
        "Стиль: мотивирующий, на «ты», вдохновляющий, по-русски.\n"
        "Собеседник --абитуриент, может не знать терминов. Объясняй теги простым языком (1 фразой, не лекцией).\n"
        "Стратегия: если теги есть --кратко объясни что это + спроси что хочет делать (продукт/исследование) → action=profile.\n"
        "Если тегов нет --спроси какая область AI привлекает → выведи теги → action=profile.\n"
        "Если спрашивает про магистратуру --расскажи про AI Talent Hub ИТМО (информация ниже).\n\n"
        "ИНФОРМАЦИЯ О МАГИСТРАТУРЕ AI TALENT HUB ИТМО:\n"
        "Онлайн-магистратура «Искусственный интеллект» (ИТМО × Napoleon IT)\n"
        "- 2 года, очная в онлайн-формате (лекции вечером, можно совмещать с работой)\n"
        "- 215 мест: 165 бюджет + 50 контракт (599 000 ₽/год, кредит 3% на 15 лет)\n"
        "- Роли: ML Engineer, Data Engineer, AI Product Developer, Data Analyst\n"
        "- Проектное обучение с реальными задачами от X5, МТС, Sber AI, Ozon Bank, Napoleon IT, Норникель\n"
        "- Выпускная работа: индустриальный проект / научная статья / AI-стартап / EdTech-курс\n"
        "- BootCamp очно в сентябре, остальное онлайн из любой точки мира\n"
        "- Диплом гос. образца очной магистратуры ИТМО\n"
        "- Лаборатории: AI Product, AI Security Lab, X5 Tech AI Lab, LLM Lab, AI in Education\n"
        "- Стипендии: до 4 100 ₽ базовая, до 27 000 ₽ повышенная, до 300 000 ₽ «Альфа-Шанс»\n"
        "- Отсрочка от армии, общежитие, военный учебный центр\n"
        "- Поступление: экзамен дистанционно / олимпиада «Я-профессионал» / Мегаолимпиада ИТМО / конкурс портфолио / конкурс ML-проектов\n"
        "- Зарплата выпускников: ML Engineer middle 170-300 тыс. ₽\n"
        "- Контакт: aitalents@itmo.ru, +7 (999) 526-79-88\n"
        "- Подать заявку: https://abitlk.itmo.ru/\n"
        "- Подробнее: https://ai.itmo.ru/ и https://abit.itmo.ru/program/master/ai\n"
        "- Telegram: https://t.me/aitalenthubnews, VK: https://vk.com/aitalenthub"
    ),
    ("guest", "other"): (
        "Стиль: профессиональный, на «вы», уважительный, по-русски.\n"
        "Собеседник: «{custom_subtype_text}». Адаптируй вопрос под роль.\n"
        "Стратегия: если теги есть --уточни профессиональный контекст (1 вопрос) → action=profile.\n"
        "Если тегов нет --спроси что ищет на Demo Day → выведи теги → action=profile."
    ),
    ("business", None): (
        "Стиль: деловой, на «вы», профессиональный, по-русски.\n"
        "Собеседник --бизнес-партнёр. Нужно выяснить: компанию, должность, цель визита (technology/hiring/investment/partnership), какие AI-проекты интересны.\n"
        "Стратегия: бизнес-партнёры ценят время. Если из первого сообщения понятны компания+задача --сразу action=profile.\n"
        "Если не хватает данных --задай 1 конкретный вопрос (компания и цель визита) → action=profile.\n"
        "Для бизнеса допустимо 2-3 вопроса (компания+цели --это минимум).\n"
        "ВАЖНО: НЕ спрашивай «в какой роли» --роль на мероприятии уже выбрана. Спрашивай «должность» (CTO, эксперт, менеджер и т.д.).\n\n"
        "ВАЖНО: при action=profile добавь дополнительные поля:\n"
        '  "company": "название компании",\n'
        '  "position": "должность в компании",\n'
        '  "partner_status": "current" или "potential",\n'
        '  "business_objectives": ["technology", "hiring", "investment", "partnership"]'
    ),
}

# Default fallback context (generic guest)
_DEFAULT_ROLE_CONTEXT = (
    "Стиль: дружелюбный, по-русски.\n"
    "Стратегия: если теги есть --уточни применение (1 вопрос) → action=profile.\n"
    "Если тегов нет --спроси что интересно → выведи теги → action=profile."
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
      {"action": "reply", "message": "..."} - continue conversation
      {"action": "profile", "interests": [...], "goals": [...], "summary": "...", ...} - done
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


# --- T007: Schedule-aware re-ranking ---


def schedule_rerank(
    candidates: list[dict],
) -> list[dict]:
    """Re-rank candidates considering schedule conflicts and room proximity.

    Each candidate dict has: project_id, score, room_number, room_name, tags.
    Applies penalties for time conflicts and bonuses for room proximity.
    """
    if not candidates:
        return []

    # Track occupied rooms (higher-ranked projects take priority)
    occupied_rooms: set[int | None] = set()
    reranked = []

    for c in candidates:
        room = c.get("room_number")
        score = c.get("score", 0.0)

        # Bonus for being in same room as previous recommendations (less walking)
        if room is not None and room in occupied_rooms:
            score += 3.0

        # Penalty for room conflicts (many projects in same room = can't see all)
        room_count = sum(1 for r in occupied_rooms if r == room) if room else 0
        if room_count > 1:
            score -= 2.0 * (room_count - 1)

        c["score"] = score
        if room is not None:
            occupied_rooms.add(room)
        reranked.append(c)

    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked


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
    """Orchestrate: embedding search → schedule rerank → LLM summaries → save.

    Pipeline:
    1. Build profile text from NL summary + tags + goals
    2. Embed profile text (1 API call ~100ms)
    3. Qdrant similarity search (top-30, <10ms)
    4. Schedule-aware rerank (in-memory)
    5. LLM summaries for top-15 (1 LLM call ~3-5s)
    6. Save to Recommendation table
    """
    import time

    from sqlalchemy import func

    from app.services.core import embedding_service

    start = time.monotonic()
    event_id = profile.event_id

    # 0. Early check: any projects loaded for this event?
    project_count = await session.scalar(
        select(func.count(Project.id)).where(Project.event_id == event_id)
    )
    if not project_count:
        return {"no_projects": True, "total": 0, "must_visit": [], "if_time": []}

    # 1. Build profile text
    parts = []
    if profile.extra_data and profile.extra_data.get("nl_summary"):
        parts.append(profile.extra_data["nl_summary"])
    if profile.selected_tags:
        parts.append(f"Интересы: {', '.join(profile.selected_tags)}")
    if profile.keywords:
        parts.append(f"Цели: {', '.join(profile.keywords)}")
    if profile.extra_data:
        ed = profile.extra_data
        if ed.get("company"):
            parts.append(f"Компания: {ed['company']}")
        if ed.get("business_objectives"):
            parts.append(f"Бизнес-цели: {', '.join(ed['business_objectives'])}")
    if profile.raw_text:
        parts.append(profile.raw_text[:500])

    profile_text = ". ".join(parts) if parts else "Интерес к AI проектам"

    # 2. Embed profile text
    try:
        profile_embedding = await embedding_service.embed_text(profile_text)
    except Exception:
        logger.warning("Profile embedding failed, falling back to empty search")
        profile_embedding = None

    # 3. Qdrant similarity search
    candidates_raw = []
    if profile_embedding:
        try:
            scored_points = await embedding_service.find_similar(
                profile_embedding, event_id, limit=30,
            )
            for sp in scored_points:
                candidates_raw.append({
                    "project_id": sp.payload["project_id"],
                    "score": sp.score * 100,  # Cosine similarity → 0-100
                    "title": sp.payload.get("title", ""),
                    "description": sp.payload.get("description", ""),
                    "tags": sp.payload.get("tags", []),
                    "room_name": sp.payload.get("room_name"),
                    "room_number": sp.payload.get("room_number"),
                })
        except Exception:
            logger.warning("Qdrant search failed")

    # Fallback: if no embedding results, load projects directly
    if not candidates_raw:
        logger.info("No embedding results, loading projects directly")
        result = await session.execute(
            select(Project)
            .where(Project.event_id == event_id)
            .options(
                selectinload(Project.tags).selectinload(ProjectTag.tag),
                selectinload(Project.room_assignments).selectinload(RoomProject.room),
            )
            .limit(30)
        )
        for p in result.scalars().all():
            tag_names = [pt.tag.name for pt in p.tags]
            room_name = None
            room_number = None
            for ra in p.room_assignments:
                room_name = ra.room.name
                room_number = ra.room.display_order + 1
                break
            # Simple tag overlap scoring as fallback
            overlap = len(set(tag_names) & set(profile.selected_tags or []))
            candidates_raw.append({
                "project_id": str(p.id),
                "score": overlap * 20.0,
                "title": p.title,
                "description": p.description[:500],
                "tags": tag_names,
                "room_name": room_name,
                "room_number": room_number,
            })
        candidates_raw.sort(key=lambda x: x["score"], reverse=True)

    # 4. Schedule-aware rerank
    reranked = schedule_rerank(candidates_raw)

    # 5. Take top-15
    top15 = reranked[:15]

    # Pad with popular projects if <10
    if len(top15) < 10:
        existing_ids = {c["project_id"] for c in top15}
        popular_result = await session.execute(
            select(Project)
            .where(Project.event_id == event_id)
            .where(Project.id.notin_([uuid.UUID(eid) for eid in existing_ids]) if existing_ids else true())
            .options(
                selectinload(Project.tags).selectinload(ProjectTag.tag),
                selectinload(Project.room_assignments).selectinload(RoomProject.room),
            )
            .order_by(Project.created_at)
            .limit(10 - len(top15))
        )
        for p in popular_result.scalars().all():
            tag_names = [pt.tag.name for pt in p.tags]
            room_name = None
            room_number = None
            for ra in p.room_assignments:
                room_name = ra.room.name
                room_number = ra.room.display_order + 1
                break
            top15.append({
                "project_id": str(p.id),
                "score": 0.0,
                "title": p.title,
                "description": p.description[:500],
                "tags": tag_names,
                "room_name": room_name,
                "room_number": room_number,
            })
        logger.info("Padded recommendations to %d with popular projects", len(top15))

    # 6. Load project details for LLM summaries
    final_ids = [uuid.UUID(c["project_id"]) for c in top15]
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
    for c in top15:
        pid = uuid.UUID(c["project_id"])
        p = final_projects.get(pid)
        if p:
            tag_names = [pt.tag.name for pt in p.tags]
            summary_input.append((p.id, p.title, p.description, tag_names))

    summaries = await generate_llm_summaries(profile, summary_input)

    # 8. Normalize scores to 0-100
    raw_scores = [c["score"] for c in top15]
    max_final = max(raw_scores) if raw_scores else 1.0
    if max_final <= 0:
        max_final = 1.0
    for c in top15:
        if max_final > 100:
            c["score"] = round(c["score"] / max_final * 100, 1)
        else:
            c["score"] = round(c["score"], 1)

    # 9. Delete old recommendations
    await session.execute(
        delete(Recommendation).where(Recommendation.guest_profile_id == profile.id)
    )

    # 10. Save new recommendations
    recs = []
    for rank_idx, c in enumerate(top15):
        pid = uuid.UUID(c["project_id"])
        category = "must_visit" if rank_idx < 8 else "if_time"
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
            relevance_score=round(c["score"], 3),
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
    """Load full project detail for a project in guest recommendation list."""
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
