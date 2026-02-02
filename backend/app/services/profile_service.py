"""Service for business profile CRUD and LLM extraction."""

import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_profile import BusinessObjective, BusinessProfile
from app.schemas.profile import BusinessProfileCreate, ExtractedProfile
from app.services.llm_client import send_chat_completion

logger = logging.getLogger(__name__)

PROFILE_EXTRACTION_PROMPT = """You are extracting structured business profile from a Russian/English text.
The user is a business partner attending Demo Day — they want to find relevant AI projects.

Extract the following fields from the user's description:
- objective: One of "investment" | "hiring" | "technology" | "partnership"
- industries: List of relevant industries mentioned (max 5), e.g. ["fintech", "edtech", "nlp"]
- tech_stack: List of technologies mentioned (max 10), e.g. ["python", "llm", "cv", "rag"]
- project_stages: List from ["idea", "mvp", "early_traction", "scaling", "mature"]
- collaboration_format: Free text describing desired collaboration type
- parsed_interests: List of extracted interest keywords (max 10)
- confidence: Float 0-1 indicating extraction quality

Output valid JSON only. If a field cannot be determined, use empty list or null.
"""


async def get_profile_by_user_event(
    session: AsyncSession,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
) -> BusinessProfile | None:
    """Get business profile for user+event combination."""
    stmt = select(BusinessProfile).where(
        BusinessProfile.user_id == user_id,
        BusinessProfile.event_id == event_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_profile_by_id(
    session: AsyncSession,
    profile_id: uuid.UUID,
) -> BusinessProfile | None:
    """Get business profile by ID."""
    stmt = select(BusinessProfile).where(BusinessProfile.id == profile_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_or_update_profile(
    session: AsyncSession,
    data: BusinessProfileCreate,
    free_text_parsed: dict | None = None,
) -> BusinessProfile:
    """Create new profile or update existing one for user+event."""
    existing = await get_profile_by_user_event(session, data.user_id, data.event_id)

    if existing:
        # Update existing profile
        existing.objective = data.objective
        existing.industries = data.industries
        existing.tech_stack = data.tech_stack
        existing.project_stages = data.project_stages
        existing.collaboration_format = data.collaboration_format
        existing.free_text_raw = data.free_text_raw
        if free_text_parsed:
            existing.free_text_parsed = free_text_parsed
        await session.commit()
        await session.refresh(existing)
        logger.info("Updated business profile: %s", existing.id)
        return existing

    # Create new profile
    profile = BusinessProfile(
        id=uuid.uuid4(),
        user_id=data.user_id,
        event_id=data.event_id,
        objective=data.objective,
        industries=data.industries,
        tech_stack=data.tech_stack,
        project_stages=data.project_stages,
        collaboration_format=data.collaboration_format,
        free_text_raw=data.free_text_raw,
        free_text_parsed=free_text_parsed,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    logger.info("Created business profile: %s", profile.id)
    return profile


async def extract_from_text(
    text: str,
    objective_hint: BusinessObjective | None = None,
) -> ExtractedProfile:
    """Extract structured profile from free-text using LLM.

    Returns ExtractedProfile with extracted fields.
    Raises RuntimeError if LLM is unavailable.
    """
    user_prompt = f"User description:\n{text}"
    if objective_hint:
        user_prompt += f"\n\nHint: User's primary objective is {objective_hint.value}"

    try:
        result = await send_chat_completion(
            system_prompt=PROFILE_EXTRACTION_PROMPT,
            user_prompt=user_prompt,
            json_mode=True,
        )

        # Parse LLM response into ExtractedProfile
        if isinstance(result, dict):
            # Normalize objective to enum if present
            obj_str = result.get("objective")
            objective = None
            if obj_str and obj_str in [o.value for o in BusinessObjective]:
                objective = BusinessObjective(obj_str)

            return ExtractedProfile(
                objective=objective,
                industries=result.get("industries", [])[:5],
                tech_stack=result.get("tech_stack", [])[:10],
                project_stages=result.get("project_stages", []),
                collaboration_format=result.get("collaboration_format"),
                parsed_interests=result.get("parsed_interests", [])[:10],
                confidence=float(result.get("confidence", 0.5)),
            )

        logger.warning("LLM returned non-dict response: %s", type(result))
        return ExtractedProfile(confidence=0.0)

    except Exception as e:
        logger.error("Profile extraction failed: %s", e)
        raise RuntimeError(f"LLM extraction failed: {e}") from e


def format_profile_summary(profile: BusinessProfile) -> str:
    """Format profile for display in Telegram message."""
    from app.models.business_profile import OBJECTIVE_DISPLAY

    lines = [f"📋 **Ваш профиль:**\n"]
    lines.append(f"🎯 Цель: {OBJECTIVE_DISPLAY.get(profile.objective, profile.objective.value)}")

    if profile.industries:
        lines.append(f"🏭 Отрасли: {', '.join(profile.industries)}")
    if profile.tech_stack:
        lines.append(f"💻 Технологии: {', '.join(profile.tech_stack)}")
    if profile.project_stages:
        stages_display = {
            "idea": "Идея",
            "mvp": "MVP",
            "early_traction": "Ранняя тяга",
            "scaling": "Масштабирование",
            "mature": "Зрелый",
        }
        stages = [stages_display.get(s, s) for s in profile.project_stages]
        lines.append(f"📈 Стадии: {', '.join(stages)}")
    if profile.collaboration_format:
        lines.append(f"🤝 Формат: {profile.collaboration_format}")

    return "\n".join(lines)
