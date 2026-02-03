"""Business Follow-up service for EPIC-015: Business Follow-up.

Manages business partner pipeline and LOI generation.
"""

import logging
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.business_followup import BusinessFollowup, PipelineStatus
from app.models.business_profile import BusinessProfile, BusinessObjective
from app.models.project import Project
from app.models.project_recommendation import ProjectRecommendation
from app.models.user import User
from app.services import followup_service

logger = logging.getLogger(__name__)

# LOI templates by objective
LOI_TEMPLATES = {
    BusinessObjective.INVESTMENT: """
Уважаемая команда проекта "{project_title}",

Меня зовут {partner_name}, я представляю интересы инвестора.
После Demo Day ваш проект привлёк моё внимание.

Мы рассматриваем возможность инвестирования в размере {budget}.
Хотел бы обсудить условия сотрудничества.

Готов провести встречу в удобное для вас время.

С уважением,
{partner_name}
""",
    BusinessObjective.PARTNERSHIP: """
Уважаемая команда проекта "{project_title}",

Меня зовут {partner_name}.
Ваш проект на Demo Day показал высокий потенциал для партнёрства.

Мы видим возможность интеграции с нашими решениями.
Предлагаю обсудить форматы сотрудничества.

С уважением,
{partner_name}
""",
    BusinessObjective.TECHNOLOGY: """
Уважаемая команда проекта "{project_title}",

Меня зовут {partner_name}.
После Demo Day заинтересовались вашей технологией.

Готовы рассмотреть возможности технологического партнёрства.
Давайте обсудим детали.

С уважением,
{partner_name}
""",
    BusinessObjective.HIRING: """
Уважаемая команда проекта "{project_title}",

Меня зовут {partner_name}, я из HR-отдела.
Ваш проект на Demo Day произвёл впечатление.

Мы ищем талантливых специалистов и хотели бы обсудить
возможности карьерного развития в нашей компании.

С уважением,
{partner_name}
""",
}


async def get_business_profile(
    session: AsyncSession,
    user_id: UUID,
) -> BusinessProfile | None:
    """Get business profile for user."""
    result = await session.execute(
        select(BusinessProfile).where(BusinessProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_pipeline_projects(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> list[BusinessFollowup]:
    """Get all projects in partner's pipeline."""
    result = await session.execute(
        select(BusinessFollowup)
        .options(selectinload(BusinessFollowup.project))
        .where(BusinessFollowup.user_id == user_id)
        .where(BusinessFollowup.event_id == event_id)
        .order_by(BusinessFollowup.created_at.desc())
    )
    return list(result.scalars().all())


async def add_to_pipeline(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    project_id: UUID,
) -> BusinessFollowup:
    """Add project to partner's pipeline."""
    # Check if already exists
    result = await session.execute(
        select(BusinessFollowup)
        .where(BusinessFollowup.user_id == user_id)
        .where(BusinessFollowup.project_id == project_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    followup = BusinessFollowup(
        user_id=user_id,
        event_id=event_id,
        project_id=project_id,
        status=PipelineStatus.interested,
    )
    session.add(followup)
    await session.flush()
    logger.info("Added to pipeline: user=%s project=%s", user_id, project_id)
    return followup


async def update_status(
    session: AsyncSession,
    followup_id: UUID,
    status: PipelineStatus,
) -> BusinessFollowup | None:
    """Update pipeline status for a project."""
    result = await session.execute(
        select(BusinessFollowup).where(BusinessFollowup.id == followup_id)
    )
    followup = result.scalar_one_or_none()
    if followup:
        followup.status = status
        await session.flush()
        logger.info("Status updated: followup=%s status=%s", followup_id, status.value)
    return followup


async def add_notes(
    session: AsyncSession,
    followup_id: UUID,
    notes: str,
) -> BusinessFollowup | None:
    """Add notes to a pipeline entry."""
    result = await session.execute(
        select(BusinessFollowup).where(BusinessFollowup.id == followup_id)
    )
    followup = result.scalar_one_or_none()
    if followup:
        followup.notes = notes
        await session.flush()
    return followup


async def generate_loi(
    session: AsyncSession,
    user_id: UUID,
    project_id: UUID,
) -> str | None:
    """Generate LOI letter for a project."""
    # Get business profile
    profile = await get_business_profile(session, user_id)
    if not profile:
        return None

    # Get project
    project_result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        return None

    # Get user name
    user_result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    # Get template
    template = LOI_TEMPLATES.get(
        profile.objective,
        LOI_TEMPLATES[BusinessObjective.PARTNERSHIP]
    )

    # Fill template
    loi = template.format(
        project_title=project.title,
        partner_name=user.full_name if user and user.full_name else "Партнёр",
        budget=profile.budget or "по договорённости",
    )

    # Mark as generated
    result = await session.execute(
        select(BusinessFollowup)
        .where(BusinessFollowup.user_id == user_id)
        .where(BusinessFollowup.project_id == project_id)
    )
    followup = result.scalar_one_or_none()
    if followup:
        followup.loi_generated = True
        await session.flush()

    return loi.strip()


def format_pipeline_message(
    followups: list[BusinessFollowup],
    profile: BusinessProfile | None,
) -> str:
    """Format pipeline for Telegram message."""
    if not followups:
        return (
            "📊 *Ваш Pipeline*\n\n"
            "У вас пока нет проектов в работе.\n"
            "Используйте /recommend для получения рекомендаций."
        )

    # Count by status
    by_status = {}
    for f in followups:
        by_status[f.status] = by_status.get(f.status, 0) + 1

    lines = [
        "📊 *Business Follow-up Pipeline*\n",
    ]

    if profile:
        lines.append(f"Цель: {profile.objective.value}")
        if profile.budget:
            lines.append(f"Бюджет: {profile.budget}")
        lines.append("")

    lines.append("*Статистика:*")
    for status, count in by_status.items():
        emoji = {
            PipelineStatus.interested: "👀",
            PipelineStatus.contacted: "📧",
            PipelineStatus.negotiating: "🤝",
            PipelineStatus.closed_won: "✅",
            PipelineStatus.closed_lost: "❌",
        }.get(status, "❓")
        lines.append(f"{emoji} {status.value}: {count}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━\n")
    lines.append("*Проекты:*\n")

    for f in followups[:10]:
        title = f.project.title if f.project else "Проект"
        lines.append(f"{f.status_emoji} *{title}*")
        if f.notes:
            lines.append(f"   _{f.notes[:50]}_")
        if f.loi_generated:
            lines.append("   📝 LOI отправлен")
        lines.append("")

    if len(followups) > 10:
        lines.append(f"... и ещё {len(followups) - 10} проектов")

    return "\n".join(lines)


async def init_pipeline_from_recommendations(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> int:
    """Initialize pipeline from existing recommendations."""
    # Get recommendations
    recs_result = await session.execute(
        select(ProjectRecommendation)
        .where(ProjectRecommendation.user_id == user_id)
    )
    recommendations = list(recs_result.scalars().all())

    added = 0
    for rec in recommendations:
        # Check if not already in pipeline
        existing = await session.execute(
            select(BusinessFollowup)
            .where(BusinessFollowup.user_id == user_id)
            .where(BusinessFollowup.project_id == rec.project_id)
        )
        if not existing.scalar_one_or_none():
            await add_to_pipeline(session, user_id, event_id, rec.project_id)
            added += 1

    return added
