"""Messaging service for unified organizer messaging.

Sends template-based messages to selected audience via Telegram bot.
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from telegram import Bot

from app.models.expert import Expert
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.services import matching_service

logger = logging.getLogger(__name__)

SEND_DELAY = 0.04


def render_template(template: str, user: User) -> str:
    """Replace {name} placeholder with user's full name."""
    return template.replace("{name}", user.full_name)


async def get_recipients(
    session: AsyncSession,
    event_id: UUID,
    roles: list[str],
    guest_subtype: str | None = None,
    room_id: str | None = None,
) -> dict[UUID, dict]:
    """Get deduplicated recipients by roles with optional filters.

    Returns dict keyed by user.id with {user, role_code} values.
    """
    recipients: dict[UUID, dict] = {}

    for role_code in roles:
        stmt = (
            select(User, Role.code)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.event_id == event_id)
            .where(Role.code == role_code)
        )

        # Guest subtype filter
        if role_code == "guest" and guest_subtype:
            stmt = stmt.where(User.guest_subtype == guest_subtype)

        result = await session.execute(stmt)
        rows = result.all()

        for user, r_code in rows:
            if user.id not in recipients:
                recipients[user.id] = {
                    "user": user,
                    "role_code": r_code,
                }

    # Expert room filter: intersect expert users with room assignment
    if "expert" in roles and room_id:
        clustering = await matching_service.get_approved_clustering(session, event_id)
        if clustering:
            era_result = await session.execute(
                select(ExpertRoomAssignment)
                .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
                .where(ExpertRoomAssignment.room_id == UUID(room_id))
                .where(ExpertRoomAssignment.status == "confirmed")
                .options(selectinload(ExpertRoomAssignment.expert))
            )
            assignments = era_result.scalars().all()
            allowed_user_ids = {
                a.expert.user_id for a in assignments if a.expert and a.expert.user_id
            }

            # Remove expert users not in this room
            to_remove = []
            for uid, rec in recipients.items():
                if rec["role_code"] == "expert" and uid not in allowed_user_ids:
                    to_remove.append(uid)
            for uid in to_remove:
                del recipients[uid]

    return recipients


async def preview(
    session: AsyncSession,
    event_id: UUID,
    template: str,
    roles: list[str],
    guest_subtype: str | None = None,
    room_id: str | None = None,
) -> dict:
    """Preview messaging: recipient count, sample message, first 10 recipients."""
    recipients = await get_recipients(session, event_id, roles, guest_subtype, room_id)

    # Sample message
    if recipients:
        first_user = next(iter(recipients.values()))["user"]
        sample_message = render_template(template, first_user)
    else:
        sample_message = template.replace("{name}", "Иван Иванов")

    # Build preview list (first 10)
    preview_list = []
    for rec in list(recipients.values())[:10]:
        user = rec["user"]
        preview_list.append(
            {
                "user_id": str(user.id),
                "full_name": user.full_name,
                "role": rec["role_code"],
                "guest_subtype": user.guest_subtype.value if user.guest_subtype else None,
            }
        )

    return {
        "recipient_count": len(recipients),
        "sample_message": sample_message,
        "recipients_preview": preview_list,
    }


async def send_messages(
    session: AsyncSession,
    event_id: UUID,
    template: str,
    roles: list[str],
    bot: Bot,
    guest_subtype: str | None = None,
    room_id: str | None = None,
) -> dict:
    """Send template messages to selected audience.

    Skips users with synthetic telegram_user_id (starting with 'guest-').
    Returns {sent, failed, skipped} counts.
    """
    recipients = await get_recipients(session, event_id, roles, guest_subtype, room_id)

    sent = 0
    failed = 0
    skipped = 0

    for rec in recipients.values():
        user = rec["user"]

        # Skip synthetic users
        if user.telegram_user_id.startswith("guest-"):
            skipped += 1
            continue

        text = render_template(template, user)

        try:
            await bot.send_message(
                chat_id=int(user.telegram_user_id),
                text=text,
            )
            sent += 1
        except Exception as e:
            logger.error("Failed to send message to %s: %s", user.full_name, e)
            failed += 1

        await asyncio.sleep(SEND_DELAY)

    return {"sent": sent, "failed": failed, "skipped": skipped}
