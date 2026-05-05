import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.user import User
from app.schemas.participation import (
    BroadcastResult,
    ParticipationRequestDetail,
    ParticipationSummary,
    UnacknowledgedList,
)
from app.services.admin import participation_service
from app.services.core import user_service

router = APIRouter(prefix="/participation", tags=["Participation"])


@router.post("/broadcast", response_model=BroadcastResult)
async def broadcast_slots(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="Нет текущего события")

    try:
        from app.services.core.bot_messenger import get_send_bot

        bot = get_send_bot()
        result = await participation_service.broadcast_slots(session, event, bot)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return BroadcastResult(**result)


@router.get("/summary", response_model=ParticipationSummary)
async def get_summary(
    room_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="Нет текущего события")

    summary = await participation_service.get_participation_summary(session, event.id, room_id)
    return ParticipationSummary(**summary)


@router.get("/unacknowledged", response_model=UnacknowledgedList)
async def get_unacknowledged(
    room_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="Нет текущего события")

    items = await participation_service.get_unacknowledged_list(session, event.id, room_id)
    return UnacknowledgedList(items=items, total=len(items))


@router.get("/{request_id}", response_model=ParticipationRequestDetail)
async def get_request_detail(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from app.models.participation import ParticipationRequest

    pr = await session.get(ParticipationRequest, request_id)
    if not pr:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    project = (
        pr.project
        if pr.project
        else await session.get(__import__("app.models.project", fromlist=["Project"]).Project, pr.project_id)
    )
    from app.models.room import Room
    from app.models.room_project import RoomProject

    room_name = "N/A"
    if pr.room_project_id:
        rp = await session.get(RoomProject, pr.room_project_id)
        if rp:
            room = await session.get(Room, rp.room_id)
            if room:
                room_name = room.name

    return ParticipationRequestDetail(
        id=pr.id,
        project_title=project.title if project else "?",
        author_name=project.author if project else "?",
        room_name=room_name,
        status=pr.status.value,
        acknowledged_at=pr.acknowledged_at,
        reminder_sent_at=pr.reminder_sent_at,
        escalated_at=pr.escalated_at,
        created_at=pr.created_at,
    )
