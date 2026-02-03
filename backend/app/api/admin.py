"""Admin API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models import User
from app.schemas.admin import DashboardResponse, ProjectListItem, RoomCoverage, RoomDetailResponse
from app.services import admin_service, user_service

router = APIRouter(prefix="/admin", tags=["Admin"])


def _check_organizer(user: User) -> None:
    """Check if user is an organizer."""
    if not user.telegram_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not an organizer"
        )
    if user.telegram_user_id not in settings.organizer_telegram_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not an organizer"
        )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics for organizer."""
    _check_organizer(current_user)

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    return await admin_service.get_dashboard_stats(db, event.id)


@router.get("/coverage", response_model=list[RoomCoverage])
async def get_coverage(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get room coverage statistics."""
    _check_organizer(current_user)

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    return await admin_service.get_coverage_stats(db, event.id)


@router.get("/rooms/{room_id}", response_model=RoomDetailResponse)
async def get_room_detail(
    room_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific room."""
    _check_organizer(current_user)

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    try:
        return await admin_service.get_room_detail(db, event.id, room_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/projects", response_model=list[ProjectListItem])
async def get_projects(
    room_id: UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get list of all projects with optional filters."""
    _check_organizer(current_user)

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    return await admin_service.get_projects_list(db, event.id, room_id, status, search)
