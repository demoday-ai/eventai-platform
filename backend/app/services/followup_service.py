"""Follow-up service for EPIC-014: Guest Follow-up.

Generates and manages follow-up packages for guests after Demo Day.
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contact_request import ContactRequest, ContactRequestStatus
from app.models.followup_package import FollowupPackage
from app.models.guest_profile import GuestProfile
from app.models.project import Project
from app.models.project_recommendation import ProjectRecommendation
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_guest_recommendations(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> list[dict]:
    """Get projects recommended to the guest."""
    result = await session.execute(
        select(ProjectRecommendation)
        .options(selectinload(ProjectRecommendation.project))
        .where(ProjectRecommendation.user_id == user_id)
    )
    recommendations = list(result.scalars().all())

    projects = []
    for rec in recommendations:
        if rec.project:
            projects.append({
                "id": str(rec.project.id),
                "title": rec.project.title,
                "description": rec.project.description[:200] if rec.project.description else "",
                "score": rec.score,
                "reason": rec.reason,
            })
    return projects


async def get_approved_contacts(
    session: AsyncSession,
    user_id: UUID,
    project_ids: list[UUID],
) -> dict[UUID, str]:
    """Get approved contacts for projects (where student agreed)."""
    if not project_ids:
        return {}

    # Get approved contact requests
    result = await session.execute(
        select(ContactRequest)
        .options(selectinload(ContactRequest.project))
        .where(ContactRequest.requester_id == user_id)
        .where(ContactRequest.project_id.in_(project_ids))
        .where(ContactRequest.status == ContactRequestStatus.approved)
    )
    requests = list(result.scalars().all())

    contacts = {}
    for req in requests:
        if req.project and req.project.user_id:
            # Get student's telegram
            student_result = await session.execute(
                select(User).where(User.id == req.project.user_id)
            )
            student = student_result.scalar_one_or_none()
            if student and student.telegram_username:
                contacts[req.project_id] = f"@{student.telegram_username}"

    return contacts


async def generate_package_content(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> dict:
    """Generate follow-up package content for a guest."""
    # Get guest profile
    profile_result = await session.execute(
        select(GuestProfile).where(GuestProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    # Get recommended projects
    projects = await get_guest_recommendations(session, user_id, event_id)

    # Get approved contacts
    project_ids = [UUID(p["id"]) for p in projects]
    contacts = await get_approved_contacts(session, user_id, project_ids)

    # Enrich projects with contact info
    for p in projects:
        pid = UUID(p["id"])
        if pid in contacts:
            p["contact"] = contacts[pid]

    return {
        "generated_at": datetime.now().isoformat(),
        "interests": profile.interests if profile else [],
        "projects": projects,
        "total_projects": len(projects),
        "projects_with_contacts": len([p for p in projects if p.get("contact")]),
    }


async def get_or_create_package(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    force_regenerate: bool = False,
) -> FollowupPackage:
    """Get existing package or create new one."""
    # Check for existing
    if not force_regenerate:
        result = await session.execute(
            select(FollowupPackage)
            .where(FollowupPackage.user_id == user_id)
            .where(FollowupPackage.event_id == event_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    # Generate new content
    content = await generate_package_content(session, user_id, event_id)

    # Create or update package
    result = await session.execute(
        select(FollowupPackage)
        .where(FollowupPackage.user_id == user_id)
        .where(FollowupPackage.event_id == event_id)
    )
    package = result.scalar_one_or_none()

    if package:
        package.content = content
        package.generated_at = datetime.now()
    else:
        package = FollowupPackage(
            user_id=user_id,
            event_id=event_id,
            content=content,
        )
        session.add(package)

    await session.flush()
    logger.info("Follow-up package generated: user=%s event=%s projects=%d",
                user_id, event_id, len(content.get("projects", [])))
    return package


async def mark_package_sent(
    session: AsyncSession,
    package_id: UUID,
) -> None:
    """Mark package as sent."""
    result = await session.execute(
        select(FollowupPackage).where(FollowupPackage.id == package_id)
    )
    package = result.scalar_one_or_none()
    if package:
        package.sent = True
        await session.flush()


def format_package_message(package: FollowupPackage) -> str:
    """Format package content for Telegram message."""
    content = package.content
    projects = content.get("projects", [])

    if not projects:
        return (
            "📭 *Follow-up пакет*\n\n"
            "К сожалению, у вас нет сохранённых проектов.\n"
            "Используйте /recommend для получения рекомендаций."
        )

    lines = [
        "📬 *Ваш Follow-up пакет*\n",
        f"Проектов: {len(projects)}",
        f"С контактами: {content.get('projects_with_contacts', 0)}\n",
        "━━━━━━━━━━━━━━━━━━━━\n",
    ]

    for i, p in enumerate(projects[:10], 1):
        lines.append(f"*{i}. {p['title']}*")
        if p.get("reason"):
            lines.append(f"_{p['reason'][:100]}_")
        if p.get("contact"):
            lines.append(f"📱 {p['contact']}")
        lines.append("")

    if len(projects) > 10:
        lines.append(f"... и ещё {len(projects) - 10} проектов")

    lines.extend([
        "\n━━━━━━━━━━━━━━━━━━━━",
        "\n💡 *Шаблон для связи:*",
        "_Здравствуйте! Видел(а) ваш проект на Demo Day._",
        "_Интересует возможность сотрудничества._",
    ])

    return "\n".join(lines)


async def get_guests_without_package(
    session: AsyncSession,
    event_id: UUID,
) -> list[User]:
    """Get guests who haven't received a follow-up package."""
    # Get all guests with profiles
    guests_result = await session.execute(
        select(User)
        .join(GuestProfile, GuestProfile.user_id == User.id)
        .where(User.telegram_chat_id.isnot(None))
    )
    all_guests = list(guests_result.scalars().all())

    # Get guests who already have packages
    packages_result = await session.execute(
        select(FollowupPackage.user_id)
        .where(FollowupPackage.event_id == event_id)
        .where(FollowupPackage.sent == True)
    )
    sent_user_ids = {row[0] for row in packages_result.all()}

    # Filter out guests with sent packages
    return [g for g in all_guests if g.id not in sent_user_ids]
