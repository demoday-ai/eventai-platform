"""Expert escalation endpoints: list, resolve."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.user import User
from app.services.admin import invite_service

router = APIRouter()


@router.get("/escalations")
async def list_escalations_endpoint(
    resolved: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.services.core import user_service

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    return await invite_service.get_escalations(session, event.id, resolved=resolved)


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation_endpoint(
    escalation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await invite_service.resolve_escalation(session, escalation_id)
    return {"status": "resolved"}
