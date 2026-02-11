"""Admin room endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas.admin import (
    RoomDetailResponse,
    RoomUpdateRequest,
    RoomUpdateResponse,
)
from app.services.admin import admin_service, audit_service
from app.services.core import user_service

router = APIRouter()


@router.get("/rooms/{room_id}", response_model=RoomDetailResponse)
async def get_room_detail(
    room_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific room."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active event")

    try:
        return await admin_service.get_room_detail(db, event.id, room_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/rooms/{room_id}", response_model=RoomUpdateResponse)
async def update_room(
    room_id: UUID,
    request: RoomUpdateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update room name/theme (organizer-managed)."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active event")

    if request.name is None and request.theme_rationale is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nothing to update",
        )

    try:
        room = await admin_service.update_room_theme(
            db,
            event.id,
            room_id,
            name=request.name,
            theme_rationale=request.theme_rationale,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    await audit_service.log_action(
        db,
        current_user,
        "room_update",
        entity_type="room",
        entity_id=str(room.id),
        details={
            "name": room.name,
            "theme_rationale": room.theme_rationale,
        },
    )

    return RoomUpdateResponse(
        id=str(room.id),
        name=room.name,
        theme_rationale=room.theme_rationale,
    )
