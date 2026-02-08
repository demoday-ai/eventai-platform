"""Admin organizer CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas.admin import OrganizerCreateRequest, OrganizerItem
from app.services.admin import organizer_service

router = APIRouter()


@router.get("/organizers", response_model=list[OrganizerItem])
async def list_organizers(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all organizers."""
    organizers = await organizer_service.list_organizers(db)
    return [
        OrganizerItem(
            id=str(o.id),
            telegram_id=o.telegram_id,
            telegram_username=o.telegram_username,
            name=o.name,
            added_by=o.added_by,
            created_at=o.created_at,
        )
        for o in organizers
    ]


@router.post("/organizers", response_model=OrganizerItem, status_code=201)
async def add_organizer(
    request: OrganizerCreateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Add a new organizer."""
    organizer = await organizer_service.add_organizer(
        db,
        telegram_id=request.telegram_id,
        telegram_username=request.telegram_username,
        name=request.name,
        added_by=current_user.full_name,
    )
    await db.commit()
    return OrganizerItem(
        id=str(organizer.id),
        telegram_id=organizer.telegram_id,
        telegram_username=organizer.telegram_username,
        name=organizer.name,
        added_by=organizer.added_by,
        created_at=organizer.created_at,
    )


@router.delete("/organizers/{organizer_id}", status_code=204)
async def delete_organizer(
    organizer_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Remove an organizer."""
    deleted = await organizer_service.remove_organizer(db, organizer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Organizer not found")
    await db.commit()
