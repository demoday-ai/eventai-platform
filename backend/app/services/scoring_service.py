"""Scoring service for EPIC-013: Expert Scoring.

Manages expert project scoring workflow.
"""

import logging
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expert import Expert
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.expert_score import ExpertScore
from app.models.project import Project
from app.models.room_project import RoomProject
from app.services import feedback_service, matching_service

logger = logging.getLogger(__name__)

# Criteria definitions
CRITERIA = [
    ("relevance", "Актуальность", "Насколько проблема актуальна"),
    ("practical_value", "Практическая значимость", "Применимость решения"),
    ("novelty", "Новизна", "Инновационность подхода"),
    ("implementation", "Реализация", "Качество технической реализации"),
    ("scalability", "Масштабируемость", "Возможность масштабирования"),
    ("research", "R&D", "Научно-исследовательский компонент"),
]


async def get_expert_by_telegram(
    session: AsyncSession,
    telegram_id: str,
) -> Expert | None:
    """Get expert by Telegram ID."""
    result = await session.execute(
        select(Expert).where(Expert.telegram_chat_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_projects_to_score(
    session: AsyncSession,
    expert_id: UUID,
    event_id: UUID,
) -> list[Project]:
    """Get projects expert should score but hasn't yet."""
    # Get expert's room
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return []

    assignment_result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.expert_id == expert_id)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status == "confirmed")
    )
    assignment = assignment_result.scalar_one_or_none()
    if not assignment or not assignment.room_id:
        return []

    # Get projects in room
    projects_result = await session.execute(
        select(Project)
        .join(RoomProject, RoomProject.project_id == Project.id)
        .where(RoomProject.room_id == assignment.room_id)
    )
    room_projects = list(projects_result.scalars().all())

    # Get already scored
    scored_result = await session.execute(
        select(ExpertScore.project_id)
        .where(ExpertScore.expert_id == expert_id)
    )
    scored_ids = {row[0] for row in scored_result.all()}

    # Filter unscored
    return [p for p in room_projects if p.id not in scored_ids]


async def get_existing_score(
    session: AsyncSession,
    expert_id: UUID,
    project_id: UUID,
) -> ExpertScore | None:
    """Get existing score for expert-project pair."""
    result = await session.execute(
        select(ExpertScore)
        .where(ExpertScore.expert_id == expert_id)
        .where(ExpertScore.project_id == project_id)
    )
    return result.scalar_one_or_none()


async def create_or_update_score(
    session: AsyncSession,
    expert_id: UUID,
    project_id: UUID,
    scores: dict,
    skipped: bool = False,
) -> ExpertScore:
    """Create or update expert score."""
    existing = await get_existing_score(session, expert_id, project_id)

    if existing:
        score = existing
    else:
        score = ExpertScore(
            expert_id=expert_id,
            project_id=project_id,
        )
        session.add(score)

    if skipped:
        score.skipped = True
    else:
        score.relevance = scores.get("relevance")
        score.practical_value = scores.get("practical_value")
        score.novelty = scores.get("novelty")
        score.implementation = scores.get("implementation")
        score.scalability = scores.get("scalability")
        score.research = scores.get("research")
        score.overall = scores.get("overall")
        score.skipped = False

    await session.flush()
    logger.info("Score saved: expert=%s project=%s skipped=%s", expert_id, project_id, skipped)
    return score


async def add_comment_to_score(
    session: AsyncSession,
    expert_id: UUID,
    project_id: UUID,
    comment: str,
) -> None:
    """Add expert comment (creates FeedbackComment)."""
    if not comment or not comment.strip():
        return

    await feedback_service.create_feedback(
        session, project_id, expert_id, comment.strip()
    )
    await session.commit()


async def get_expert_scores_summary(
    session: AsyncSession,
    expert_id: UUID,
    event_id: UUID,
) -> dict:
    """Get summary of expert's scoring progress."""
    to_score = await get_projects_to_score(session, expert_id, event_id)

    # Count completed scores
    result = await session.execute(
        select(ExpertScore)
        .where(ExpertScore.expert_id == expert_id)
    )
    scored = list(result.scalars().all())

    return {
        "pending": len(to_score),
        "completed": len(scored),
        "skipped": len([s for s in scored if s.skipped]),
    }


def format_score_criteria(current_scores: dict, current_criterion: str | None = None) -> str:
    """Format criteria progress display."""
    lines = []
    for key, name, _ in CRITERIA:
        value = current_scores.get(key)
        if value is not None:
            lines.append(f"✅ {name}: {value}/3")
        elif key == current_criterion:
            lines.append(f"👉 *{name}*")
        else:
            lines.append(f"⬜ {name}")
    return "\n".join(lines)
