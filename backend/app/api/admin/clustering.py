"""Admin clustering endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas.admin import SuggestThemesRequest, SuggestThemesResponse
from app.services.admin import clustering_service
from app.services.core import user_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/clustering/suggest-themes", response_model=SuggestThemesResponse)
async def suggest_themes(
    request: SuggestThemesRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Suggest room themes based on project tags and descriptions.

    Analyzes all projects using LLM and returns suggested theme names.
    Organizer can edit these before running clustering.
    """
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    try:
        themes = await clustering_service.suggest_room_themes(
            db, event.id, request.num_rooms
        )
        return SuggestThemesResponse(themes=themes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        # Graceful degradation: return generic themes
        logger.exception("Failed to suggest themes: %s", e)
        themes = [f"Зал {i + 1}" for i in range(request.num_rooms)]
        return SuggestThemesResponse(themes=themes)
