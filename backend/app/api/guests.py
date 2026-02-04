"""Guest profiling REST API endpoints (EPIC-005)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services import profiling_service

router = APIRouter(tags=["guests"])


# --- Request/Response schemas ---


class ProfileCreateRequest(BaseModel):
    user_id: uuid.UUID
    event_id: uuid.UUID
    selected_tags: list[str]
    raw_text: str | None = None


class GuestProfileResponse(BaseModel):
    id: uuid.UUID
    selected_tags: list[str]
    extracted_tags: list[str]
    keywords: list[str]
    raw_text: str | None
    all_interests: list[str]
    created_at: str
    updated_at: str


class TagInfoResponse(BaseModel):
    name: str
    project_count: int


# --- Endpoints ---


@router.get("/profile/tags")
async def get_available_tags(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get all tags available for profiling with project counts."""
    tags = await profiling_service.get_available_tags(session, event_id)
    return {"tags": [{"name": name, "project_count": cnt} for name, cnt in tags]}


@router.get("/profile/{user_id}")
async def get_profile(
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get guest profile for user and event."""
    from sqlalchemy import select
    from app.models.guest_profile import GuestProfile

    result = await session.execute(
        select(GuestProfile)
        .where(GuestProfile.user_id == user_id)
        .where(GuestProfile.event_id == event_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    all_interests = list(dict.fromkeys(profile.selected_tags))
    return {
        "id": str(profile.id),
        "selected_tags": profile.selected_tags,
        "keywords": profile.keywords,
        "raw_text": profile.raw_text,
        "all_interests": all_interests,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }


@router.post("/profile")
async def create_or_update_profile(
    req: ProfileCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create or update guest profile. Extracts interests from raw_text if provided."""
    profile = await profiling_service.get_or_create_profile(
        session, req.user_id, req.event_id
    )

    # Extract interests from text if provided
    extracted_tags = []
    keywords = []
    if req.raw_text:
        available = await profiling_service.get_available_tags(session, req.event_id)
        available_names = [t[0] for t in available]
        result = await profiling_service.extract_interests_from_text(
            req.raw_text, available_names
        )
        extracted_tags = result.get("tags", [])
        keywords = result.get("keywords", [])

    all_tags = list(dict.fromkeys(req.selected_tags + extracted_tags))
    profile = await profiling_service.save_profile(
        session, profile, all_tags, keywords, req.raw_text
    )

    all_interests = list(dict.fromkeys(profile.selected_tags))
    return {
        "id": str(profile.id),
        "selected_tags": profile.selected_tags,
        "extracted_tags": profile.extracted_tags,
        "keywords": profile.keywords,
        "raw_text": profile.raw_text,
        "all_interests": all_interests,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }


@router.post("/recommendations/{user_id}")
async def generate_recommendations(
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Generate personalized project recommendations for guest."""
    from sqlalchemy import select
    from app.models.guest_profile import GuestProfile

    result = await session.execute(
        select(GuestProfile)
        .where(GuestProfile.user_id == user_id)
        .where(GuestProfile.event_id == event_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=400, detail="Profile not found. Create profile first.")

    data = await profiling_service.generate_recommendations(session, profile)
    return data


@router.get("/recommendations/{user_id}")
async def get_recommendations(
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get existing recommendations for guest."""
    from sqlalchemy import select
    from app.models.guest_profile import GuestProfile

    result = await session.execute(
        select(GuestProfile)
        .where(GuestProfile.user_id == user_id)
        .where(GuestProfile.event_id == event_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    data = await profiling_service.get_recommendations(session, profile.id)
    if not data:
        raise HTTPException(status_code=404, detail="No recommendations found")
    return data


@router.get("/recommendations/{user_id}/project/{project_id}")
async def get_project_detail(
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get full project detail from guest's recommendation list."""
    from sqlalchemy import select
    from app.models.guest_profile import GuestProfile

    result = await session.execute(
        select(GuestProfile)
        .where(GuestProfile.user_id == user_id)
        .where(GuestProfile.event_id == event_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    detail = await profiling_service.get_project_detail(session, profile.id, project_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Project not found in recommendations")
    return detail
