"""Expert coverage endpoints: summary, gaps, room detail."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.user import User
from app.services.admin import coverage_service

router = APIRouter()


@router.get("/coverage")
async def coverage_dashboard_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.services.core import user_service

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    dashboard = await coverage_service.get_coverage_summary(session, event.id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="No approved clustering")
    return dashboard


@router.get("/coverage/gaps")
async def coverage_gaps_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.services.core import user_service

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    gaps = await coverage_service.get_coverage_gaps(session, event.id)
    if not gaps:
        raise HTTPException(status_code=404, detail="No approved clustering")
    return gaps


@router.get("/coverage/{room_id}")
async def coverage_room_detail_endpoint(
    room_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.services.core import user_service

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    detail = await coverage_service.get_room_detail(session, event.id, room_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Room coverage data not found")
    return detail
