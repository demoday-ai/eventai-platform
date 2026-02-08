"""Admin dashboard & coverage endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas.admin import (
    Alert,
    DashboardResponse,
    ExpertStats,
    GuestStats,
    RoomCoverage,
    RoomStats,
    StudentStats,
)
from app.services.admin import admin_service
from app.services.core import user_service

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics for organizer."""

    event = await user_service.get_current_event(db)
    if not event:
        return DashboardResponse(
            students=StudentStats(total=0, confirmed=0, pending=0, declined=0),
            experts=ExpertStats(total=0, confirmed=0, pending=0, invited=0),
            guests=GuestStats(total=0, by_subtype=[]),
            rooms=RoomStats(total=0, with_experts=0, without_experts=0),
            alerts=[Alert(severity="info", message="Нет активного мероприятия. Загрузите проекты для начала работы.")],
        )

    return await admin_service.get_dashboard_stats(db, event.id)


@router.get("/coverage", response_model=list[RoomCoverage])
async def get_coverage(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get room coverage statistics."""

    event = await user_service.get_current_event(db)
    if not event:
        return []

    return await admin_service.get_coverage_stats(db, event.id)
