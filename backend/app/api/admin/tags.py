"""Admin tag management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas.admin import (
    TagListResponse,
    TagReplaceRequest,
    TagReplaceResponse,
    TagSuggestResponse,
    TagUpsertRequest,
    TagUpsertResponse,
)
from app.services.admin import admin_service, audit_service
from app.services.core import user_service

router = APIRouter()


@router.get("/tags", response_model=TagListResponse)
async def list_tags(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List available tags."""
    tags = await admin_service.list_tags(db)
    return TagListResponse(tags=tags)


@router.post("/tags", response_model=TagUpsertResponse)
async def add_tags(
    request: TagUpsertRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Add optional base tags for conference."""
    added, skipped = await admin_service.add_tags(db, request.tags)

    await audit_service.log_action(
        db, current_user, "tags_add",
        entity_type="tags",
        details={"added": added, "skipped": skipped},
    )

    return TagUpsertResponse(added=added, skipped=skipped)


@router.post("/tags/seed", response_model=TagUpsertResponse)
async def seed_default_tags(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Seed default tags (EdTech, NLP, CV, etc.)."""
    added, skipped = await admin_service.seed_default_tags(db)

    await audit_service.log_action(
        db, current_user, "tags_seed",
        entity_type="tags",
        details={"added": added, "skipped": skipped},
    )

    return TagUpsertResponse(added=added, skipped=skipped)


@router.delete("/tags/{tag_name}", status_code=204)
async def delete_tag(
    tag_name: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a single tag and its project associations."""
    deleted = await admin_service.delete_tag(db, tag_name)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    await audit_service.log_action(
        db, current_user, "tags_delete",
        entity_type="tags",
        details={"deleted": tag_name},
    )


@router.post("/tags/suggest", response_model=TagSuggestResponse)
async def suggest_tags(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Suggest tags based on project descriptions using LLM."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    result = await admin_service.suggest_tags(db, event.id)
    return TagSuggestResponse(**result)


@router.put("/tags", response_model=TagReplaceResponse)
async def replace_tags(
    request: TagReplaceRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Replace all tags with a new set."""
    result = await admin_service.replace_tags(db, request.tags)

    await audit_service.log_action(
        db, current_user, "tags_replace",
        entity_type="tags",
        details={"added": result["added"], "removed": result["removed"]},
    )

    return TagReplaceResponse(**result)
