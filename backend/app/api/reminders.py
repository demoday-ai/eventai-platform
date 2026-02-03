"""REST API for EPIC-007: DD Reminders.

Endpoints for viewing reminder batch history and details.
Organizer-only access.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_session
from app.models.reminder import (
    ReminderNotification as Notification,
    ReminderBatch,
    ReminderBatchStatus,
    ReminderType,
)
from app.schemas.reminder import (
    ReminderBatchDetail,
    ReminderBatchSummary,
    ReminderPreview,
)
from app.services import reminder_service, user_service

router = APIRouter(prefix="/reminders", tags=["Reminders"])


def is_organizer(telegram_user_id: str | None) -> bool:
    """Check if user is an organizer."""
    if not telegram_user_id:
        return False
    return telegram_user_id in settings.organizer_ids


class PreviewRequest(BaseModel):
    reminder_type: ReminderType


class BatchListResponse(BaseModel):
    batches: list[ReminderBatchSummary]


# T044: GET /api/v1/reminders/batches
@router.get("/batches", response_model=BatchListResponse)
async def list_batches(
    status_filter: ReminderBatchStatus | None = None,
    reminder_type: ReminderType | None = None,
    telegram_user_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """List reminder batches for the current event."""
    if not is_organizer(telegram_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для организаторов",
        )

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Нет активного события"
        )

    query = select(ReminderBatch).where(ReminderBatch.event_id == event.id)

    if status_filter:
        query = query.where(ReminderBatch.status == status_filter)
    if reminder_type:
        query = query.where(ReminderBatch.reminder_type == reminder_type)

    query = query.order_by(ReminderBatch.started_at.desc())

    result = await session.execute(query)
    batches = result.scalars().all()

    return BatchListResponse(
        batches=[
            ReminderBatchSummary(
                id=b.id,
                reminder_type=b.reminder_type,
                status=b.status,
                initiated_by_name=b.initiated_by_name,
                total_recipients=b.total_recipients,
                sent_count=b.sent_count,
                failed_count=b.failed_count,
                skipped_count=b.skipped_count,
                started_at=b.started_at,
                completed_at=b.completed_at,
            )
            for b in batches
        ]
    )


# T045: GET /api/v1/reminders/batches/{batch_id}
@router.get("/batches/{batch_id}", response_model=ReminderBatchDetail)
async def get_batch(
    batch_id: UUID,
    telegram_user_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Get detailed information about a specific reminder batch."""
    if not is_organizer(telegram_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для организаторов",
        )

    result = await session.execute(
        select(ReminderBatch)
        .where(ReminderBatch.id == batch_id)
        .options(selectinload(ReminderBatch.notifications))
    )
    batch = result.scalars().first()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пакет рассылки не найден"
        )

    # Aggregate by recipient type
    by_recipient_type = {}
    for notification in batch.notifications:
        rt = notification.recipient_type.value
        if rt not in by_recipient_type:
            by_recipient_type[rt] = {"total": 0, "sent": 0, "failed": 0}
        by_recipient_type[rt]["total"] += 1
        if notification.status.value == "sent":
            by_recipient_type[rt]["sent"] += 1
        elif notification.status.value == "failed":
            by_recipient_type[rt]["failed"] += 1

    return ReminderBatchDetail(
        id=batch.id,
        reminder_type=batch.reminder_type,
        status=batch.status,
        initiated_by_name=batch.initiated_by_name,
        total_recipients=batch.total_recipients,
        sent_count=batch.sent_count,
        failed_count=batch.failed_count,
        skipped_count=batch.skipped_count,
        started_at=batch.started_at,
        completed_at=batch.completed_at,
        by_recipient_type=by_recipient_type,
    )


# T046: POST /api/v1/reminders/preview
@router.post("/preview", response_model=ReminderPreview)
async def preview_reminders(
    request: PreviewRequest,
    telegram_user_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Preview recipients and message counts before sending."""
    if not is_organizer(telegram_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для организаторов",
        )

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Нет активного события"
        )

    preview = await reminder_service.get_preview(session, event.id, request.reminder_type)

    return ReminderPreview(
        reminder_type=preview["reminder_type"],
        by_role=preview["by_role"],
        total_recipients=preview["total_recipients"],
        total_skipped=preview["total_skipped"],
        duplicate_warning=preview.get("duplicate_warning"),
    )
