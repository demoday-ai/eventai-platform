from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.user import EventResponse
from app.services import user_service

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/current", response_model=EventResponse)
async def get_current_event(session: AsyncSession = Depends(get_session)):
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Нет активного события"
        )
    return event
