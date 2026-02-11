"""Admin event management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.models.event import Event
from app.schemas.admin import EventCreateRequest, EventUpdateRequest
from app.schemas.user import EventResponse
from app.services.admin import audit_service
from app.services.core import user_service

router = APIRouter()


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    request: EventCreateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new event."""
    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be >= start_date",
        )

    # Check if an event already exists
    result = await db.execute(select(Event).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active event already exists",
        )

    event = Event(
        name=request.name,
        start_date=request.start_date,
        end_date=request.end_date,
        description=request.description,
    )
    db.add(event)

    await audit_service.log_action(
        db,
        current_user,
        "event_create",
        entity_type="event",
        details={"name": request.name, "start_date": str(request.start_date), "end_date": str(request.end_date)},
    )

    await db.commit()
    await db.refresh(event)
    return event


@router.patch("/events/current", response_model=EventResponse)
async def update_current_event(
    request: EventUpdateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update current event details (name, dates, description)."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active event")

    # Determine effective dates for validation
    new_start = request.start_date if request.start_date is not None else event.start_date
    new_end = request.end_date if request.end_date is not None else event.end_date
    if new_end < new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be >= start_date",
        )

    # Apply non-None fields
    changes = {}
    for field in ("name", "start_date", "end_date", "description"):
        value = getattr(request, field)
        if value is not None:
            changes[field] = str(value)
            setattr(event, field, value)

    await audit_service.log_action(
        db,
        current_user,
        "event_update",
        entity_type="event",
        entity_id=str(event.id),
        details=changes,
    )

    await db.commit()
    await db.refresh(event)
    return event
