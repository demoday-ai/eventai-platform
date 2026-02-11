"""Contact service for EPIC-010: Contact Requests.

Handles contact exchange between users and project authors.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contact_request import ContactRequest, ContactRequestStatus
from app.models.project import Project
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_student_for_project(
    session: AsyncSession,
    project_id: UUID,
) -> User | None:
    """Get the student user associated with a project.

    Uses telegram_contact from project to find the user.
    """
    # Get project
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        return None

    # Find user by telegram_contact
    # telegram_contact might be @username or just username
    contact = project.telegram_contact
    if contact.startswith("@"):
        contact = contact[1:]

    result = await session.execute(select(User).where(User.username == contact))
    return result.scalar_one_or_none()


async def get_existing_request(
    session: AsyncSession,
    requester_id: UUID,
    project_id: UUID,
) -> ContactRequest | None:
    """Get existing request from requester to project."""
    result = await session.execute(
        select(ContactRequest)
        .where(ContactRequest.requester_id == requester_id)
        .where(ContactRequest.project_id == project_id)
    )
    return result.scalar_one_or_none()


async def create_request(
    session: AsyncSession,
    requester_id: UUID,
    project_id: UUID,
    student_user_id: UUID,
    message: str | None = None,
) -> ContactRequest:
    """Create a new contact request."""
    request = ContactRequest(
        requester_id=requester_id,
        project_id=project_id,
        student_user_id=student_user_id,
        status=ContactRequestStatus.PENDING.value,
        requester_message=message,
    )
    session.add(request)
    await session.flush()
    logger.info(
        "Contact request created: requester=%s project=%s student=%s", requester_id, project_id, student_user_id
    )
    return request


async def get_pending_requests_for_student(
    session: AsyncSession,
    student_user_id: UUID,
) -> list[ContactRequest]:
    """Get all pending requests for a student."""
    result = await session.execute(
        select(ContactRequest)
        .where(ContactRequest.student_user_id == student_user_id)
        .where(ContactRequest.status == ContactRequestStatus.PENDING.value)
        .options(
            selectinload(ContactRequest.requester),
            selectinload(ContactRequest.project),
        )
        .order_by(ContactRequest.created_at.desc())
    )
    return list(result.scalars().all())


async def get_request_by_id(
    session: AsyncSession,
    request_id: UUID,
) -> ContactRequest | None:
    """Get contact request by ID with relationships loaded."""
    result = await session.execute(
        select(ContactRequest)
        .where(ContactRequest.id == request_id)
        .options(
            selectinload(ContactRequest.requester),
            selectinload(ContactRequest.student),
            selectinload(ContactRequest.project),
        )
    )
    return result.scalar_one_or_none()


async def approve_request(
    session: AsyncSession,
    request_id: UUID,
) -> ContactRequest | None:
    """Approve a contact request."""
    request = await get_request_by_id(session, request_id)
    if not request:
        return None

    if request.status != ContactRequestStatus.PENDING.value:
        logger.warning("Cannot approve non-pending request %s", request_id)
        return request

    request.status = ContactRequestStatus.APPROVED.value
    request.responded_at = datetime.now(timezone.utc)
    await session.commit()

    logger.info("Contact request approved: %s", request_id)
    return request


async def reject_request(
    session: AsyncSession,
    request_id: UUID,
) -> ContactRequest | None:
    """Reject a contact request."""
    request = await get_request_by_id(session, request_id)
    if not request:
        return None

    if request.status != ContactRequestStatus.PENDING.value:
        logger.warning("Cannot reject non-pending request %s", request_id)
        return request

    request.status = ContactRequestStatus.REJECTED.value
    request.responded_at = datetime.now(timezone.utc)
    await session.commit()

    logger.info("Contact request rejected: %s", request_id)
    return request


def get_user_contact(user: User) -> str | None:
    """Get user's contact (Telegram username)."""
    if user.username:
        return f"@{user.username}"
    return None


def format_requester_info(user: User, role_name: str | None) -> str:
    """Format requester information for display."""
    name = user.full_name or user.username or "Пользователь"
    if role_name:
        return f"{name} ({role_name})"
    return name
