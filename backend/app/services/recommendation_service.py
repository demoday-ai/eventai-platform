"""Service for project recommendation generation and management."""

import logging
import uuid
from typing import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.business_profile import BusinessProfile
from app.models.project import Project
from app.models.project_recommendation import ProjectRecommendation
from app.models.project_tag import ProjectTag
from app.models.tag import Tag
from app.services.llm_client import send_chat_completion

logger = logging.getLogger(__name__)

RANKING_PROMPT = """You are ranking Demo Day projects for a business partner.

Business partner profile:
- Objective: {objective}
- Industries: {industries}
- Technologies: {tech_stack}
- Preferred stages: {stages}
- Collaboration: {collaboration}

Rank the following projects by business relevance (0-100 score).
Consider:
- For investors: focus on stage, market potential, team
- For hiring: focus on team skills, technologies used
- For technology partners: focus on tech stack, integration potential
- For strategic partners: focus on industry fit, scale

Output JSON array: [{{"project_id": "<id>", "score": <0-100>, "explanation": "<why>"}}]
Order by score descending. Include ALL projects.
"""


async def filter_by_tags(
    session: AsyncSession,
    event_id: uuid.UUID,
    industries: list[str] | None,
    tech_stack: list[str] | None,
    limit: int = 30,
) -> list[tuple[Project, int]]:
    """Filter projects by tag match, return (project, match_count) tuples.

    Stage 1 of two-stage recommendation: fast deterministic filtering.
    """
    # Get all projects for event with their tags
    stmt = (
        select(Project)
        .where(Project.event_id == event_id)
        .options(selectinload(Project.tags).selectinload(ProjectTag.tag))
    )
    result = await session.execute(stmt)
    projects = result.scalars().all()

    # Build search terms from profile
    search_terms = set()
    if industries:
        search_terms.update(t.lower() for t in industries)
    if tech_stack:
        search_terms.update(t.lower() for t in tech_stack)

    if not search_terms:
        # No filters — return all projects with score 0
        return [(p, 0) for p in projects[:limit]]

    # Score each project by tag match
    scored = []
    for project in projects:
        project_tags = {pt.tag.name.lower() for pt in project.tags if pt.tag}
        match_count = len(search_terms & project_tags)
        scored.append((project, match_count))

    # Sort by match count descending, take top N
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


async def rank_with_llm(
    profile: BusinessProfile,
    projects: list[tuple[Project, int]],
) -> list[dict]:
    """Re-rank filtered projects using LLM for business context.

    Stage 2 of two-stage recommendation: LLM adds business relevance.
    Returns list of {project_id, score, explanation}.
    """
    if not projects:
        return []

    # Build project summaries for LLM
    project_summaries = []
    for project, tag_score in projects:
        tags = [pt.tag.name for pt in project.tags if pt.tag]
        project_summaries.append({
            "id": str(project.id),
            "title": project.title,
            "description": project.description[:500],  # Truncate for token limit
            "tags": tags[:10],
            "tag_match_score": tag_score,
        })

    user_prompt = f"Projects to rank:\n{project_summaries}"

    try:
        result = await send_chat_completion(
            system_prompt=RANKING_PROMPT.format(
                objective=profile.objective.value,
                industries=", ".join(profile.industries or []),
                tech_stack=", ".join(profile.tech_stack or []),
                stages=", ".join(profile.project_stages or []),
                collaboration=profile.collaboration_format or "any",
            ),
            user_prompt=user_prompt,
            json_mode=True,
        )

        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "rankings" in result:
            return result["rankings"]

        logger.warning("Unexpected LLM ranking response format")
        return []

    except Exception as e:
        logger.error("LLM ranking failed: %s", e)
        raise RuntimeError(f"LLM ranking failed: {e}") from e


async def generate_recommendations(
    session: AsyncSession,
    profile: BusinessProfile,
    max_results: int = 15,
    broaden_on_empty: bool = True,
) -> list[ProjectRecommendation]:
    """Generate recommendations for a business profile.

    Two-stage approach:
    1. Filter by tags (fast, deterministic)
    2. Re-rank with LLM (adds business context)

    Falls back to tag-only results if LLM fails.
    If broaden_on_empty=True and no matches, tries without filters.
    """
    # Clear existing recommendations
    await session.execute(
        delete(ProjectRecommendation).where(
            ProjectRecommendation.profile_id == profile.id
        )
    )

    # Stage 1: Filter by tags
    filtered = await filter_by_tags(
        session,
        profile.event_id,
        profile.industries,
        profile.tech_stack,
        limit=30,
    )

    # T039: If no matches, try without filters (broaden criteria)
    if not filtered and broaden_on_empty:
        logger.info(
            "No tag matches for profile %s, broadening to all projects",
            profile.id,
        )
        filtered = await filter_by_tags(
            session,
            profile.event_id,
            industries=None,
            tech_stack=None,
            limit=30,
        )

    if not filtered:
        logger.warning("No projects found for event %s", profile.event_id)
        return []

    # Stage 2: Try LLM ranking
    rankings = []
    try:
        rankings = await rank_with_llm(profile, filtered)
    except RuntimeError:
        logger.warning("LLM ranking failed, using tag-based scores only")

    # Build project_id -> ranking map
    ranking_map = {r["project_id"]: r for r in rankings}

    # Create recommendation records
    recommendations = []
    for rank_idx, (project, tag_score) in enumerate(filtered[:max_results], start=1):
        project_id_str = str(project.id)
        llm_data = ranking_map.get(project_id_str, {})

        # Use LLM score if available, otherwise scale tag score
        score = llm_data.get("score", min(tag_score * 20, 100))
        explanation = llm_data.get("explanation")

        rec = ProjectRecommendation(
            id=uuid.uuid4(),
            profile_id=profile.id,
            project_id=project.id,
            relevance_score=int(score),
            relevance_explanation=explanation,
            rank=rank_idx,
            is_bookmarked=False,
            is_viewed=False,
        )
        session.add(rec)
        recommendations.append(rec)

    await session.commit()

    # Re-sort by score if LLM provided rankings
    if rankings:
        recommendations.sort(key=lambda r: r.relevance_score, reverse=True)
        for idx, rec in enumerate(recommendations, start=1):
            rec.rank = idx
        await session.commit()

    logger.info(
        "Generated %d recommendations for profile %s",
        len(recommendations),
        profile.id,
    )
    return recommendations


async def get_recommendations(
    session: AsyncSession,
    profile_id: uuid.UUID,
    page: int = 1,
    page_size: int = 5,
) -> tuple[list[ProjectRecommendation], int]:
    """Get paginated recommendations for a profile.

    Returns (recommendations, total_count).
    """
    # Get total count
    count_stmt = select(func.count()).where(
        ProjectRecommendation.profile_id == profile_id
    )
    total = (await session.execute(count_stmt)).scalar() or 0

    # Get page
    offset = (page - 1) * page_size
    stmt = (
        select(ProjectRecommendation)
        .where(ProjectRecommendation.profile_id == profile_id)
        .order_by(ProjectRecommendation.rank)
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    recs = list(result.scalars().all())

    return recs, total


async def get_recommendation_with_project(
    session: AsyncSession,
    recommendation_id: uuid.UUID,
) -> ProjectRecommendation | None:
    """Get a single recommendation with its project loaded."""
    stmt = (
        select(ProjectRecommendation)
        .where(ProjectRecommendation.id == recommendation_id)
        .options(selectinload(ProjectRecommendation.project))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def toggle_bookmark(
    session: AsyncSession,
    recommendation_id: uuid.UUID,
) -> ProjectRecommendation | None:
    """Toggle bookmark status for a recommendation."""
    rec = await get_recommendation_with_project(session, recommendation_id)
    if rec:
        rec.is_bookmarked = not rec.is_bookmarked
        await session.commit()
        await session.refresh(rec)
    return rec


async def mark_viewed(
    session: AsyncSession,
    recommendation_id: uuid.UUID,
) -> ProjectRecommendation | None:
    """Mark a recommendation as viewed."""
    rec = await get_recommendation_with_project(session, recommendation_id)
    if rec:
        rec.is_viewed = True
        await session.commit()
        await session.refresh(rec)
    return rec
