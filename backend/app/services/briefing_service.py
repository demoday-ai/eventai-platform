"""Briefing service for EPIC-008: Expert Project Overview.

Generates and sends project briefings to experts before Demo Day.
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from telegram import Bot

from app.models.expert import Expert
from app.models.expert_briefing import BriefingStatus, ExpertBriefing
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.project import Project
from app.models.room_project import RoomProject
from app.services import github_service, matching_service

logger = logging.getLogger(__name__)

# Telegram message limit
MAX_MESSAGE_LENGTH = 4000
# Rate limiting
SEND_DELAY = 0.04


async def get_room_projects(session: AsyncSession, room_id: UUID) -> list[Project]:
    """Get all projects in a room."""
    result = await session.execute(
        select(Project)
        .join(RoomProject, RoomProject.project_id == Project.id)
        .where(RoomProject.room_id == room_id)
        .options(selectinload(Project.tags))
    )
    return list(result.scalars().all())


async def format_project_card(project: Project, github_status: github_service.GitHubStatus) -> str:
    """Format a single project card for the briefing.

    Returns text block with project info.
    """
    # Title and author
    lines = [f"📌 *{project.title}*"]

    # Author
    if project.author:
        lines.append(f"👤 {project.author}")

    # Description (truncated to 200 chars)
    if project.description:
        desc = project.description[:200]
        if len(project.description) > 200:
            desc += "..."
        lines.append(f"📝 {desc}")

    # Tags
    if project.tags:
        tag_names = [t.name for t in project.tags[:5]]
        lines.append(f"🏷️ {', '.join(tag_names)}")

    # Tech stack
    if project.tech_stack:
        lines.append(f"🛠️ {project.tech_stack}")

    # GitHub status
    lines.append(f"GitHub: {github_status.display}")

    # Artifacts
    artifacts = []
    if project.presentation_url:
        artifacts.append(f"[📊 Презентация]({project.presentation_url})")
    if project.demo_url:
        artifacts.append(f"[🎬 Демо]({project.demo_url})")
    if artifacts:
        lines.append(" | ".join(artifacts))

    return "\n".join(lines)


async def format_briefing(
    expert: Expert, room_name: str, projects: list[Project]
) -> list[str]:
    """Format full briefing for an expert.

    Returns list of message texts (split if too long).
    """
    if not projects:
        return [
            f"📋 *Брифинг для {expert.name}*\n\n"
            f"Зал: {room_name}\n\n"
            f"В вашей комнате пока нет проектов."
        ]

    # Header
    header = (
        f"📋 *Брифинг для {expert.name}*\n\n"
        f"Зал: {room_name}\n"
        f"Проектов: {len(projects)}\n\n"
        f"{'─' * 20}\n"
    )

    # Fetch GitHub statuses in parallel
    github_tasks = [
        github_service.get_repo_status(p.github_url)
        for p in projects
    ]
    github_statuses = await asyncio.gather(*github_tasks)

    # Format project cards
    cards = []
    for project, gh_status in zip(projects, github_statuses):
        card = await format_project_card(project, gh_status)
        cards.append(card)

    # Split into messages if needed
    messages = []
    current_message = header
    card_separator = f"\n\n{'─' * 20}\n\n"

    for i, card in enumerate(cards):
        test_message = current_message + card_separator + card if current_message != header else current_message + card

        if len(test_message) > MAX_MESSAGE_LENGTH:
            # Current message is full, start new one
            if current_message != header:
                messages.append(current_message)
            current_message = f"📋 *Продолжение брифинга* ({i + 1}/{len(cards)})\n\n{card}"
        else:
            if current_message == header:
                current_message = current_message + card
            else:
                current_message = current_message + card_separator + card

    if current_message:
        messages.append(current_message)

    return messages


async def send_briefing(
    session: AsyncSession,
    expert: Expert,
    room_id: UUID,
    room_name: str,
    event_id: UUID,
    bot: Bot,
) -> ExpertBriefing:
    """Send briefing to a single expert.

    Creates ExpertBriefing record and sends messages.
    """
    # Get projects for room
    projects = await get_room_projects(session, room_id)

    # Create briefing record
    briefing = ExpertBriefing(
        expert_id=expert.id,
        room_id=room_id,
        event_id=event_id,
        project_count=len(projects),
        status=BriefingStatus.PENDING,
    )
    session.add(briefing)
    await session.flush()

    # Format messages
    messages = await format_briefing(expert, room_name, projects)
    briefing.message_count = len(messages)

    # Send
    tg_id = expert.telegram_chat_id
    if not tg_id:
        briefing.status = BriefingStatus.SKIPPED
        briefing.error_message = "No telegram_chat_id"
        logger.warning("Expert %s has no telegram_chat_id", expert.name)
        return briefing

    try:
        for msg in messages:
            await bot.send_message(
                chat_id=int(tg_id),
                text=msg,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            await asyncio.sleep(SEND_DELAY)

        briefing.status = BriefingStatus.SENT
        briefing.sent_at = datetime.now(timezone.utc)
        logger.info("Briefing sent to expert %s (%d projects)", expert.name, len(projects))

    except Exception as e:
        briefing.status = BriefingStatus.FAILED
        briefing.error_message = str(e)[:500]
        logger.error("Failed to send briefing to %s: %s", expert.name, e)

    return briefing


async def send_all_briefings(
    session: AsyncSession,
    event_id: UUID,
    bot: Bot,
) -> dict:
    """Send briefings to all confirmed experts.

    Returns summary dict with sent/failed/skipped counts.
    """
    # Get approved clustering
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        logger.warning("No approved clustering for event %s", event_id)
        return {"sent": 0, "failed": 0, "skipped": 0, "error": "No approved clustering"}

    # Get confirmed expert assignments
    result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status == "confirmed")
        .options(
            selectinload(ExpertRoomAssignment.expert),
            selectinload(ExpertRoomAssignment.room),
        )
    )
    assignments = result.scalars().all()

    logger.info("Sending briefings to %d experts", len(assignments))

    sent = 0
    failed = 0
    skipped = 0

    for assignment in assignments:
        expert = assignment.expert
        room = assignment.room

        if not room:
            logger.warning("Expert %s has no room assigned", expert.name)
            skipped += 1
            continue

        briefing = await send_briefing(
            session, expert, room.id, room.name, event_id, bot
        )

        if briefing.status == BriefingStatus.SENT:
            sent += 1
        elif briefing.status == BriefingStatus.FAILED:
            failed += 1
        else:
            skipped += 1

    await session.commit()

    return {"sent": sent, "failed": failed, "skipped": skipped}


async def get_briefing_preview(session: AsyncSession, event_id: UUID) -> dict:
    """Get preview of briefing recipients.

    Returns count of experts who will receive briefings.
    """
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return {"expert_count": 0, "error": "No approved clustering"}

    result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status == "confirmed")
    )
    assignments = result.scalars().all()

    # Count with telegram_chat_id
    with_telegram = 0
    for a in assignments:
        if a.expert and a.expert.telegram_chat_id:
            with_telegram += 1

    return {
        "expert_count": len(assignments),
        "with_telegram": with_telegram,
        "without_telegram": len(assignments) - with_telegram,
    }
