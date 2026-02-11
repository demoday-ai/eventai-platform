"""Q&A service for EPIC-009: Q&A Helper.

Generates context-aware questions for guests and business partners.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_profile import BusinessObjective, BusinessProfile
from app.models.guest_profile import GuestProfile
from app.models.project import Project
from app.models.project_recommendation import ProjectRecommendation
from app.models.qa_suggestion import QASuggestion, QuestionType
from app.models.user import GuestSubtype, User
from app.prompts.guest.qa import (
    build_business_qa_prompt,
    build_comparison_matrix_prompt,
    build_guest_qa_prompt,
)
from app.services.core import llm_client

logger = logging.getLogger(__name__)

# Cache TTL
CACHE_TTL_HOURS = 1


def get_question_type(user: User, business_profile: BusinessProfile | None = None) -> QuestionType:
    """Determine question type based on user role and subtype."""
    # Business partner
    if business_profile:
        objective = business_profile.objective
        if objective == BusinessObjective.INVESTMENT:
            return QuestionType.BUSINESS_INVESTOR
        elif objective == BusinessObjective.HIRING:
            return QuestionType.BUSINESS_HR
        elif objective == BusinessObjective.TECHNOLOGY:
            return QuestionType.BUSINESS_TECH
        else:
            return QuestionType.BUSINESS_PARTNER

    # Guest
    if user.guest_subtype == GuestSubtype.APPLICANT:
        return QuestionType.GUEST_APPLICANT
    elif user.guest_subtype == GuestSubtype.STUDENT:
        return QuestionType.GUEST_STUDENT
    else:
        return QuestionType.GUEST_GENERAL


def build_guest_prompt(
    user: User,
    project: Project,
    guest_profile: GuestProfile | None,
) -> tuple[str, str]:
    """Build LLM prompt for guest questions."""
    subtype_map = {
        GuestSubtype.APPLICANT: "Абитуриент (интересуется обучением)",
        GuestSubtype.STUDENT: "Студент (интересуется обучением и технологиями)",
        GuestSubtype.OTHER: "Гость (общий интерес)",
    }
    subtype_desc = subtype_map.get(user.guest_subtype, "Гость")

    interests = ""
    if guest_profile:
        all_tags = (guest_profile.selected_tags or []) + (guest_profile.extracted_tags or [])
        if all_tags:
            interests = f"\nИнтересы: {', '.join(all_tags)}"
        if guest_profile.keywords:
            interests += f"\nКлючевые слова: {', '.join(guest_profile.keywords)}"

    return build_guest_qa_prompt(
        subtype_desc=subtype_desc,
        interests=interests,
        project_title=project.title,
        project_description=project.description[:500] if project.description else "Не указано",
        project_tech_stack=project.tech_stack or "Не указано",
    )


def build_business_prompt(
    business_profile: BusinessProfile,
    project: Project,
) -> tuple[str, str]:
    """Build LLM prompt for business partner questions."""
    return build_business_qa_prompt(
        objective=business_profile.objective,
        industries=business_profile.industries or [],
        tech_stack=business_profile.tech_stack or [],
        project_title=project.title,
        project_description=project.description[:500] if project.description else "Не указано",
        project_tech_stack=project.tech_stack or "Не указано",
    )


async def get_cached_questions(
    session: AsyncSession,
    user_id: UUID,
    project_id: UUID,
    question_type: QuestionType,
) -> list[str] | None:
    """Get cached questions if not expired."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(QASuggestion)
        .where(QASuggestion.user_id == user_id)
        .where(QASuggestion.project_id == project_id)
        .where(QASuggestion.question_type == question_type.value)
        .where(QASuggestion.expires_at > now)
    )
    cached = result.scalar_one_or_none()
    if cached:
        logger.info("Cache hit for user=%s project=%s", user_id, project_id)
        return cached.questions.get("questions", [])
    return None


async def save_questions(
    session: AsyncSession,
    user_id: UUID,
    project_id: UUID,
    question_type: QuestionType,
    questions: list[str],
) -> QASuggestion:
    """Save generated questions to cache."""
    now = datetime.now(timezone.utc)
    suggestion = QASuggestion(
        user_id=user_id,
        project_id=project_id,
        question_type=question_type.value,
        questions={"questions": questions},
        generated_at=now,
        expires_at=now + timedelta(hours=CACHE_TTL_HOURS),
    )
    session.add(suggestion)
    await session.flush()
    return suggestion


async def generate_questions(
    session: AsyncSession,
    user: User,
    project: Project,
    guest_profile: GuestProfile | None = None,
    business_profile: BusinessProfile | None = None,
) -> list[str]:
    """Generate questions via LLM."""
    question_type = get_question_type(user, business_profile)

    # Check cache first
    cached = await get_cached_questions(session, user.id, project.id, question_type)
    if cached:
        return cached

    # Build prompt based on user type
    if business_profile:
        system_prompt, user_prompt = build_business_prompt(business_profile, project)
    else:
        system_prompt, user_prompt = build_guest_prompt(user, project, guest_profile)

    # Call LLM
    try:
        response = await llm_client.send_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )
        questions = response.get("questions", [])
        if not questions:
            logger.warning("LLM returned empty questions for project %s", project.id)
            questions = get_fallback_questions(question_type)
    except Exception as e:
        logger.error("LLM failed for Q&A: %s", e)
        questions = get_fallback_questions(question_type)

    # Save to cache
    await save_questions(session, user.id, project.id, question_type, questions)
    await session.commit()

    return questions


def get_fallback_questions(question_type: QuestionType) -> list[str]:
    """Return fallback questions when LLM fails."""
    fallback = {
        QuestionType.GUEST_GENERAL: [
            "Какую проблему решает ваш проект?",
            "Кто ваша целевая аудитория?",
            "Каковы планы развития проекта?",
        ],
        QuestionType.GUEST_APPLICANT: [
            "Какие технологии вы использовали и почему?",
            "Что было самым сложным в проекте?",
            "Какие навыки вы приобрели?",
        ],
        QuestionType.GUEST_STUDENT: [
            "Какие технологии вы использовали и почему?",
            "Что было самым сложным в проекте?",
            "Какие навыки вы приобрели?",
        ],
        QuestionType.GUEST_PRACTITIONER: [
            "Какую архитектуру вы выбрали и почему?",
            "Какие метрики качества вы используете?",
            "Как вы решали проблему масштабирования?",
        ],
        QuestionType.BUSINESS_INVESTOR: [
            "Какой размер рынка вы оцениваете?",
            "Какая у вас бизнес-модель?",
            "На какой стадии находится проект?",
        ],
        QuestionType.BUSINESS_HR: [
            "Какой технический стек использует команда?",
            "Сколько человек в команде?",
            "Готовы ли вы рассмотреть предложения о работе?",
        ],
        QuestionType.BUSINESS_TECH: [
            "Есть ли у проекта API для интеграции?",
            "Какие ограничения масштабирования?",
            "Какая лицензия на код?",
        ],
        QuestionType.BUSINESS_PARTNER: [
            "Готовы ли вы к пилотному проекту?",
            "Какие условия сотрудничества рассматриваете?",
            "Есть ли у вас кейсы внедрения?",
        ],
    }
    return fallback.get(question_type, fallback[QuestionType.GUEST_GENERAL])


async def get_user_recommendations(
    session: AsyncSession,
    user_id: UUID,
) -> list[Project]:
    """Get projects recommended to user."""
    result = await session.execute(
        select(Project)
        .join(ProjectRecommendation, ProjectRecommendation.project_id == Project.id)
        .where(ProjectRecommendation.user_id == user_id)
        .order_by(ProjectRecommendation.score.desc())
    )
    return list(result.scalars().all())


# Comparison matrix functions


def get_default_criteria(
    user: User,
    business_profile: BusinessProfile | None = None,
) -> list[str]:
    """Get default comparison criteria based on user profile."""
    if business_profile:
        return [
            "Стадия проекта",
            "Размер команды",
            "Технический стек",
            "Бизнес-модель",
            "Готовность к пилоту",
        ]
    else:
        return [
            "Тематика",
            "Технологии",
            "Практическая применимость",
            "Инновационность",
            "Зрелость проекта",
        ]


def build_matrix_prompt(
    projects: list[Project],
    criteria: list[str],
) -> tuple[str, str]:
    """Build LLM prompt for comparison matrix."""
    project_list = "\n".join(
        [f"- {p.title}: {p.description[:200] if p.description else 'Нет описания'}" for p in projects]
    )
    return build_comparison_matrix_prompt(project_list, criteria)


async def generate_comparison_matrix(
    session: AsyncSession,
    projects: list[Project],
    criteria: list[str],
) -> dict:
    """Generate comparison matrix via LLM."""
    if len(projects) < 2:
        return {"error": "Нужно минимум 2 проекта для сравнения"}

    system_prompt, user_prompt = build_matrix_prompt(projects, criteria)

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )
        return response.get("matrix", {})
    except Exception as e:
        logger.error("LLM failed for comparison matrix: %s", e)
        return {"error": "Не удалось сгенерировать матрицу"}


def format_matrix_text(matrix: dict, criteria: list[str]) -> str:
    """Format comparison matrix as text table for Telegram."""
    if "error" in matrix:
        return f"❌ {matrix['error']}"

    if not matrix:
        return "❌ Матрица пуста"

    # Build table header
    projects = list(matrix.keys())
    header = "📊 *Матрица сравнения*\n\n"

    lines = []
    for criterion in criteria:
        line = f"*{criterion}:*\n"
        for project in projects:
            value = matrix.get(project, {}).get(criterion, "—")
            line += f"  • {project[:20]}: {value}\n"
        lines.append(line)

    return header + "\n".join(lines)
