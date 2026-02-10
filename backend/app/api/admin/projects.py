"""Admin project list endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas.admin import ProjectListItem
from app.services.admin import admin_service, project_service
from app.services.core import user_service

router = APIRouter()


@router.get("/projects", response_model=list[ProjectListItem])
async def get_projects(
    room_id: UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get list of all projects with optional filters."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    return await admin_service.get_projects_list(db, event.id, room_id, status, search)


@router.post("/projects/generate-tags")
async def generate_project_tags(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate tags for projects without tags using heuristic + LLM."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    result = await project_service.generate_missing_tags(db, event.id)
    return result
