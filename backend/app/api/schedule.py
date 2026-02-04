"""Schedule and notification REST API endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_organizer, get_current_user
from app.database import get_session
from app.models import User
from app.schemas.schedule import (
    NotificationDashboard,
    NotificationListResponse,
    ReminderCancelRequest,
    ReminderCancelResult,
    ReminderPreview,
    ReminderSendRequest,
    ReminderSendResult,
    ScheduleApproveResult,
    ScheduleChangeItem,
    ScheduleChangeListResponse,
    ScheduleGenerateRequest,
    ScheduleGenerateResult,
    ScheduleResponse,
    ScheduleSlotResponse,
    SlotUpdateRequest,
    SlotUpdateResult,
)
from app.services import audit_service, notification_service, schedule_service, user_service
from app.services.notification_service import CancellationWindowClosedError

router = APIRouter(tags=["Schedule"])


# ========== Schedule Endpoints (T015) ==========


@router.post("/schedule/generate", response_model=ScheduleGenerateResult, status_code=201)
async def generate_schedule(
    request: ScheduleGenerateRequest = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Auto-generate schedule from approved clustering."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    try:
        result = await schedule_service.generate_schedule(
            db,
            event.id,
            clustering_run_id=request.clustering_run_id if request else None,
            day1_start=request.day1_start if request else None,
            day1_end=request.day1_end if request else None,
            day2_start=request.day2_start if request else None,
            day2_end=request.day2_end if request else None,
            slot_duration_minutes=request.slot_duration_minutes if request else 15,
        )
        await audit_service.log_action(
            db, current_user, "schedule_generate",
            entity_type="schedule",
            details={"total_slots": result.total_slots},
        )
        await db.commit()
        return result
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schedule", response_model=ScheduleResponse)
async def get_schedule(
    room_id: UUID | None = None,
    day: date | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get full schedule."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    return await schedule_service.get_schedule(
        db, event.id, room_id=room_id, day=day, status=status
    )


@router.post("/schedule/approve", response_model=ScheduleApproveResult)
async def approve_schedule(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Approve the schedule."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    try:
        result = await schedule_service.approve_schedule(db, event.id)
        await audit_service.log_action(
            db, current_user, "schedule_approve",
            entity_type="schedule",
        )
        await db.commit()
        return ScheduleApproveResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/schedule/slots/{slot_id}", response_model=SlotUpdateResult)
async def update_slot(
    slot_id: UUID,
    request: SlotUpdateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Update a schedule slot (T030)."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    try:
        slot, change_log = await schedule_service.update_slot(
            db,
            slot_id,
            {
                "start_time": request.start_time,
                "end_time": request.end_time,
                "room_id": request.room_id,
                "status": request.status,
            },
            changed_by_user_id=current_user.id,
        )

        # Queue timing shift notifications
        notifications_queued = 0
        if change_log:
            notifications_queued = await notification_service.queue_timing_shift_notifications(
                db, change_log, event.id
            )

        await audit_service.log_action(
            db, current_user, "slot_update",
            entity_type="schedule_slot", entity_id=str(slot_id),
            details={"notifications_queued": notifications_queued},
        )

        return SlotUpdateResult(
            slot=ScheduleSlotResponse(
                id=slot.id,
                room_id=slot.room_id,
                room_name=slot.room.name if slot.room else "Unknown",
                project_id=slot.project_id,
                project_title=slot.project.title if slot.project else "Unknown",
                project_author=slot.project.author if slot.project else None,
                start_time=slot.start_time,
                end_time=slot.end_time,
                display_order=slot.display_order,
                status=slot.status,
            ),
            change_log_id=change_log.id if change_log else slot.id,
            notifications_queued=notifications_queued,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/schedule/changes", response_model=ScheduleChangeListResponse)
async def get_schedule_changes(
    slot_id: UUID | None = None,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List schedule change logs (T034)."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    changes = await schedule_service.get_change_log(
        db, event.id, slot_id=slot_id, limit=limit
    )

    items = [
        ScheduleChangeItem(
            id=c.id,
            slot_id=c.schedule_slot_id,
            project_title=c.schedule_slot.project.title if c.schedule_slot and c.schedule_slot.project else None,
            change_type=c.change_type,
            old_start_time=c.old_start_time,
            new_start_time=c.new_start_time,
            old_room_name=c.old_room.name if c.old_room else None,
            new_room_name=c.new_room.name if c.new_room else None,
            changed_by=c.changed_by.full_name if c.changed_by else None,
            created_at=c.created_at,
            notifications_sent=c.notifications_sent,
        )
        for c in changes
    ]

    return ScheduleChangeListResponse(total=len(items), items=items)


# ========== Reminder Endpoints (T016) ==========


@router.get("/reminders/preview", response_model=ReminderPreview)
async def preview_reminders(
    day: date | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Preview pending reminders."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    # Check schedule is approved
    if not await schedule_service.is_schedule_approved(db, event.id):
        raise HTTPException(status_code=400, detail="Schedule not approved yet")

    target_day = day or event.start_date
    return await notification_service.preview_reminders(db, event.id, target_day)


@router.post("/reminders/cancel", response_model=ReminderCancelResult)
async def cancel_reminders(
    request: ReminderCancelRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Cancel pending eve-of-DD reminders."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    try:
        cancelled = await notification_service.cancel_reminders(
            db, event.id, request.day
        )
        return ReminderCancelResult(cancelled_count=cancelled, day=request.day)
    except CancellationWindowClosedError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reminders/send", response_model=ReminderSendResult)
async def send_reminders(
    request: ReminderSendRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Manually trigger reminder send."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    # Check schedule is approved
    if not await schedule_service.is_schedule_approved(db, event.id):
        raise HTTPException(status_code=400, detail="Schedule not approved")

    bot_app = getattr(http_request.app.state, "bot_app", None)
    bot = getattr(bot_app, "bot", None) if bot_app else None
    if not bot:
        raise HTTPException(status_code=503, detail="Bot is not configured")

    try:
        result = await notification_service.send_eve_reminders(
            db, event.id, request.day, bot=bot
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== Notification Dashboard Endpoints (T032, T033) ==========


@router.get("/notifications/dashboard", response_model=NotificationDashboard)
async def get_notification_dashboard(
    type: str | None = None,
    day: date | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    """Notification delivery dashboard (T032)."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    return await notification_service.get_notification_dashboard(
        db, event.id, type_filter=type, day_filter=day
    )


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    user_id: UUID | None = None,
    type: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List notifications (T033)."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=400, detail="No active event")

    return await notification_service.get_notifications(
        db,
        event.id,
        user_id=user_id,
        type_filter=type,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
