"""Business profile API endpoints (EPIC-006)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.role import RoleCode
from app.models.user import User
from app.schemas.profile import (
    BusinessProfileCreate,
    BusinessProfileResponse,
    ExtractedProfile,
    ExtractRequest,
    ProjectRecommendationResponse,
    RecommendationUpdate,
    RecommendationsPage,
)
from app.services import profile_service, recommendation_service, user_service

router = APIRouter(prefix="/profiles", tags=["Profiles"])


async def _require_business_role(
    user: User,
    session: AsyncSession,
) -> None:
    """Validate user has business role."""
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Нет активного события",
        )

    role = await user_service.get_user_role_with_info(session, user.id, event.id)
    if not role or role.code != RoleCode.BUSINESS.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только бизнес-партнёрам",
        )


@router.post("/business", response_model=BusinessProfileResponse)
async def create_or_update_business_profile(
    body: BusinessProfileCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create or update business profile for current user."""
    await _require_business_role(user, session)

    event = await user_service.get_current_event(session)

    # Override user_id and event_id with current context
    create_data = BusinessProfileCreate(
        user_id=user.id,
        event_id=event.id,
        objective=body.objective,
        industries=body.industries,
        tech_stack=body.tech_stack,
        project_stages=body.project_stages,
        collaboration_format=body.collaboration_format,
        free_text_raw=body.free_text_raw,
    )

    profile = await profile_service.create_or_update_profile(session, create_data)

    return BusinessProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        event_id=profile.event_id,
        objective=profile.objective,
        industries=profile.industries,
        tech_stack=profile.tech_stack,
        project_stages=profile.project_stages,
        collaboration_format=profile.collaboration_format,
        free_text_raw=profile.free_text_raw,
        free_text_parsed=profile.free_text_parsed,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        recommendations_count=0,
    )


@router.get("/business", response_model=BusinessProfileResponse | None)
async def get_business_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get current user's business profile for active event."""
    await _require_business_role(user, session)

    event = await user_service.get_current_event(session)
    profile = await profile_service.get_profile_by_user_event(
        session, user.id, event.id
    )

    if not profile:
        return None

    # Count recommendations
    recs, total = await recommendation_service.get_recommendations(
        session, profile.id, page=1, page_size=1
    )

    return BusinessProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        event_id=profile.event_id,
        objective=profile.objective,
        industries=profile.industries,
        tech_stack=profile.tech_stack,
        project_stages=profile.project_stages,
        collaboration_format=profile.collaboration_format,
        free_text_raw=profile.free_text_raw,
        free_text_parsed=profile.free_text_parsed,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        recommendations_count=total,
    )


@router.post("/business/extract", response_model=ExtractedProfile)
async def extract_profile_from_text(
    body: ExtractRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Extract structured profile from free text using LLM."""
    await _require_business_role(user, session)

    try:
        extracted = await profile_service.extract_from_text(
            body.text, objective_hint=body.objective
        )
        return extracted
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM extraction unavailable: {e}",
        ) from e


@router.get(
    "/business/{profile_id}/recommendations",
    response_model=RecommendationsPage,
)
async def get_recommendations(
    profile_id: uuid.UUID,
    page: int = 1,
    page_size: int = 5,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get paginated recommendations for a business profile."""
    await _require_business_role(user, session)

    # Verify profile belongs to user
    profile = await profile_service.get_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден",
        )
    if profile.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён",
        )

    recs, total = await recommendation_service.get_recommendations(
        session, profile_id, page=page, page_size=page_size
    )

    # Build response items
    items = []
    for rec in recs:
        rec_with_proj = await recommendation_service.get_recommendation_with_project(
            session, rec.id
        )
        if rec_with_proj and rec_with_proj.project:
            project = rec_with_proj.project
            tags = [pt.tag.name for pt in project.tags if pt.tag]

            items.append(
                ProjectRecommendationResponse(
                    id=rec.id,
                    project_id=project.id,
                    project_title=project.title,
                    project_description=project.description,
                    project_author=project.author,
                    project_tags=tags,
                    hall=project.hall,
                    time_slot=project.time_slot,
                    relevance_score=rec.relevance_score,
                    relevance_explanation=rec.relevance_explanation,
                    rank=rec.rank,
                    is_bookmarked=rec.is_bookmarked,
                    is_viewed=rec.is_viewed,
                )
            )

    total_pages = (total + page_size - 1) // page_size

    return RecommendationsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=page < total_pages,
    )


@router.post(
    "/business/{profile_id}/recommendations",
    response_model=RecommendationsPage,
)
async def regenerate_recommendations(
    profile_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Regenerate recommendations for a business profile."""
    await _require_business_role(user, session)

    # Verify profile belongs to user
    profile = await profile_service.get_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден",
        )
    if profile.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён",
        )

    # Generate new recommendations
    await recommendation_service.generate_recommendations(
        session, profile, max_results=15
    )

    # Return first page
    return await get_recommendations(
        profile_id=profile_id,
        page=1,
        page_size=5,
        user=user,
        session=session,
    )


@router.patch(
    "/business/{profile_id}/recommendations/{recommendation_id}",
    response_model=ProjectRecommendationResponse,
)
async def update_recommendation(
    profile_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    body: RecommendationUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update recommendation status (viewed, bookmarked)."""
    await _require_business_role(user, session)

    # Verify profile belongs to user
    profile = await profile_service.get_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден",
        )
    if profile.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён",
        )

    rec = await recommendation_service.get_recommendation_with_project(
        session, recommendation_id
    )
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рекомендация не найдена",
        )
    if rec.profile_id != profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Рекомендация не принадлежит профилю",
        )

    # Apply updates
    if body.is_viewed is not None and body.is_viewed:
        await recommendation_service.mark_viewed(session, recommendation_id)

    if body.is_bookmarked is not None:
        # Toggle if different from current
        if body.is_bookmarked != rec.is_bookmarked:
            await recommendation_service.toggle_bookmark(session, recommendation_id)

    # Reload and return
    rec = await recommendation_service.get_recommendation_with_project(
        session, recommendation_id
    )
    project = rec.project
    tags = [pt.tag.name for pt in project.tags if pt.tag]

    return ProjectRecommendationResponse(
        id=rec.id,
        project_id=project.id,
        project_title=project.title,
        project_description=project.description,
        project_author=project.author,
        project_tags=tags,
        hall=project.hall,
        time_slot=project.time_slot,
        relevance_score=rec.relevance_score,
        relevance_explanation=rec.relevance_explanation,
        rank=rec.rank,
        is_bookmarked=rec.is_bookmarked,
        is_viewed=rec.is_viewed,
    )
