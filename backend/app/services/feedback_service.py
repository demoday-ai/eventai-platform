"""Feedback service for EPIC-012: Student Feedback.

Processes expert feedback with AI and manages moderation workflow.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.feedback_comment import FeedbackComment, ModerationStatus
from app.models.project import Project
from app.services import llm_client

logger = logging.getLogger(__name__)


async def process_comment(text: str) -> dict:
    """Process a feedback comment with LLM.

    Returns dict with is_constructive, category, processed_text.
    """
    system_prompt = """Ты — модератор обратной связи на Demo Day. Анализируй комментарии экспертов.

Задачи:
1. Определи, конструктивен ли комментарий (true/false)
   - Неконструктивно: оскорбления, "херня", "плохо" без пояснений
   - Конструктивно: конкретные замечания, предложения, похвала с деталями
2. Категоризируй: technical (код, архитектура), product (идея, рынок), presentation (подача, слайды), general
3. Перепиши в позитивном ключе, сохраняя суть

Ответь JSON:
{
  "is_constructive": true/false,
  "category": "technical|product|presentation|general",
  "processed_text": "переписанный текст"
}"""

    user_prompt = f"Комментарий эксперта:\n\n{text}"

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )
        return {
            "is_constructive": response.get("is_constructive", True),
            "category": response.get("category", "general"),
            "processed_text": response.get("processed_text", text),
        }
    except Exception as e:
        logger.error("LLM failed for feedback processing: %s", e)
        return {
            "is_constructive": True,
            "category": "general",
            "processed_text": text,
        }


async def create_feedback(
    session: AsyncSession,
    project_id: UUID,
    expert_id: UUID,
    text: str,
) -> FeedbackComment:
    """Create and process a new feedback comment."""
    # Process with LLM
    processed = await process_comment(text)

    feedback = FeedbackComment(
        project_id=project_id,
        expert_id=expert_id,
        original_text=text,
        processed_text=processed["processed_text"],
        category=processed["category"],
        is_constructive=processed["is_constructive"],
        moderation_status=ModerationStatus.PENDING.value,
    )
    session.add(feedback)
    await session.flush()

    logger.info(
        "Feedback created: project=%s expert=%s constructive=%s",
        project_id, expert_id, processed["is_constructive"]
    )
    return feedback


async def get_projects_with_pending_feedback(
    session: AsyncSession,
    event_id: UUID,
) -> list[dict]:
    """Get projects that have pending feedback for moderation."""
    result = await session.execute(
        select(
            Project.id,
            Project.title,
            func.count(FeedbackComment.id).label("pending_count")
        )
        .join(FeedbackComment, FeedbackComment.project_id == Project.id)
        .where(Project.event_id == event_id)
        .where(FeedbackComment.moderation_status == ModerationStatus.PENDING.value)
        .group_by(Project.id, Project.title)
        .having(func.count(FeedbackComment.id) > 0)
    )

    return [
        {"id": row[0], "title": row[1], "pending_count": row[2]}
        for row in result.all()
    ]


async def get_pending_feedback_for_project(
    session: AsyncSession,
    project_id: UUID,
) -> list[FeedbackComment]:
    """Get all pending feedback for a project."""
    result = await session.execute(
        select(FeedbackComment)
        .where(FeedbackComment.project_id == project_id)
        .where(FeedbackComment.moderation_status == ModerationStatus.PENDING.value)
        .options(selectinload(FeedbackComment.expert))
        .order_by(FeedbackComment.created_at)
    )
    return list(result.scalars().all())


async def get_feedback_by_id(
    session: AsyncSession,
    feedback_id: UUID,
) -> FeedbackComment | None:
    """Get feedback by ID with relationships."""
    result = await session.execute(
        select(FeedbackComment)
        .where(FeedbackComment.id == feedback_id)
        .options(
            selectinload(FeedbackComment.project),
            selectinload(FeedbackComment.expert),
        )
    )
    return result.scalar_one_or_none()


async def approve_feedback(
    session: AsyncSession,
    feedback_id: UUID,
) -> FeedbackComment | None:
    """Approve a feedback comment."""
    feedback = await get_feedback_by_id(session, feedback_id)
    if not feedback:
        return None

    feedback.moderation_status = ModerationStatus.APPROVED.value
    await session.commit()

    logger.info("Feedback approved: %s", feedback_id)
    return feedback


async def reject_feedback(
    session: AsyncSession,
    feedback_id: UUID,
    reason: str | None = None,
) -> FeedbackComment | None:
    """Reject a feedback comment."""
    feedback = await get_feedback_by_id(session, feedback_id)
    if not feedback:
        return None

    feedback.moderation_status = ModerationStatus.REJECTED.value
    feedback.moderator_notes = reason
    await session.commit()

    logger.info("Feedback rejected: %s", feedback_id)
    return feedback


async def edit_feedback(
    session: AsyncSession,
    feedback_id: UUID,
    new_text: str,
) -> FeedbackComment | None:
    """Edit and approve a feedback comment."""
    feedback = await get_feedback_by_id(session, feedback_id)
    if not feedback:
        return None

    feedback.processed_text = new_text
    feedback.moderation_status = ModerationStatus.EDITED.value
    await session.commit()

    logger.info("Feedback edited: %s", feedback_id)
    return feedback


async def get_approved_feedback_for_project(
    session: AsyncSession,
    project_id: UUID,
) -> list[FeedbackComment]:
    """Get all approved/edited feedback for a project."""
    result = await session.execute(
        select(FeedbackComment)
        .where(FeedbackComment.project_id == project_id)
        .where(FeedbackComment.moderation_status.in_([
            ModerationStatus.APPROVED.value,
            ModerationStatus.EDITED.value,
        ]))
        .where(FeedbackComment.sent_at.is_(None))
        .options(selectinload(FeedbackComment.expert))
    )
    return list(result.scalars().all())


async def send_feedback_to_student(
    session: AsyncSession,
    project_id: UUID,
    bot,
) -> int:
    """Send all approved feedback to student.

    Returns number of feedbacks sent.
    """
    # Get project with student contact
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        return 0

    # Get approved feedback
    feedbacks = await get_approved_feedback_for_project(session, project_id)
    if not feedbacks:
        return 0

    # Find student user by telegram_contact
    contact = project.telegram_contact
    if contact.startswith("@"):
        contact = contact[1:]

    from app.models.user import User
    user_result = await session.execute(
        select(User).where(User.username == contact)
    )
    student = user_result.scalar_one_or_none()

    if not student or not student.telegram_user_id:
        logger.warning("Student not found for project %s", project_id)
        return 0

    # Format message
    message = format_feedback_message(project.title, feedbacks)

    # Send
    try:
        await bot.send_message(
            chat_id=int(student.telegram_user_id),
            text=message,
            parse_mode="Markdown",
        )

        # Mark as sent
        now = datetime.now(timezone.utc)
        for fb in feedbacks:
            fb.sent_at = now
        await session.commit()

        logger.info("Feedback sent to student for project %s: %d items", project_id, len(feedbacks))
        return len(feedbacks)

    except Exception as e:
        logger.error("Failed to send feedback to student: %s", e)
        return 0


def format_feedback_message(project_title: str, feedbacks: list[FeedbackComment]) -> str:
    """Format feedback for student message."""
    lines = [
        "📝 *Обратная связь по проекту*",
        f"_{project_title}_",
        "",
        f"Вы получили {len(feedbacks)} отзывов от экспертов:",
        "",
    ]

    # Group by category
    by_category = {}
    for fb in feedbacks:
        cat = fb.category or "general"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(fb)

    category_emoji = {
        "technical": "🔧",
        "product": "💡",
        "presentation": "🎤",
        "general": "📋",
    }
    category_name = {
        "technical": "Техническое",
        "product": "Продукт/идея",
        "presentation": "Презентация",
        "general": "Общее",
    }

    for cat, items in by_category.items():
        emoji = category_emoji.get(cat, "📋")
        name = category_name.get(cat, "Другое")
        lines.append(f"{emoji} *{name}:*")
        for fb in items:
            text = fb.processed_text or fb.original_text
            lines.append(f"• {text}")
        lines.append("")

    lines.append("💪 Удачи в развитии проекта!")

    return "\n".join(lines)
