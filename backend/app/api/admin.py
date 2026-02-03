"""Admin API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models import User
from app.schemas.admin import DashboardResponse, RoomCoverage
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
