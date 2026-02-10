"""Tag management service (split from admin_service)."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project
from app.repos import tag_repo

logger = logging.getLogger(__name__)

TAG_SUGGEST_SYSTEM = (
    "Ты AI-ассистент для организатора Demo Day. "
    "Проанализируй названия и описания проектов и предложи 10-20 тегов "
    "для классификации этих проектов по тематикам. "
    "Теги должны быть короткие (1-2 слова), на английском языке. "
    "Верни JSON строго в формате:\n"
    '{"tags": ["EdTech", "NLP", "CV", ...]}'
)


DEFAULT_TAGS = [
    "NLP",
    "CV",
    "ML",
    "DL",
    "LLM",
    "RAG",
    "Agents",
    "Recsys",
    "EdTech",
    "FinTech",
    "MedTech",
    "AgriTech",
    "Security",
    "MLOps",
    "ASR",
    "TTS",
    "RL",
    "TimeSeries",
    "Backend",
    "Industrial",
    "Other",
]


async def list_tags(db: AsyncSession) -> list[str]:
    """List all available tags."""
    return await tag_repo.list_all(db)


async def add_tags(db: AsyncSession, tags: list[str]) -> tuple[list[str], list[str]]:
    """Add new tags (dedupe by lowercase). Returns (added, skipped)."""
    cleaned = [t.strip() for t in tags if t and t.strip()]
    if not cleaned:
        return [], []

    existing = await tag_repo.get_existing_names(db)

    added: list[str] = []
    skipped: list[str] = []
    for tag in cleaned:
        if tag.lower() in existing:
            skipped.append(tag)
            continue
        await tag_repo.create(db, tag)
        existing.add(tag.lower())
        added.append(tag)

    if added:
        await db.commit()

    return added, skipped


async def seed_default_tags(db: AsyncSession) -> tuple[list[str], list[str]]:
    """Seed the default tag set. Returns (added, skipped)."""
    return await add_tags(db, DEFAULT_TAGS)


async def delete_tag(db: AsyncSession, tag_name: str) -> bool:
    """Delete a single tag and its project associations. Returns True if found."""
    deleted = await tag_repo.delete_by_name(db, tag_name)
    if deleted:
        await db.commit()
    return deleted


async def suggest_tags(db: AsyncSession, event_id: UUID) -> dict:
    """Analyze project descriptions and suggest tags via LLM."""
    from app.services.core import llm_client

    result = await db.execute(
        select(Project.title, Project.description)
        .where(Project.event_id == event_id)
        .limit(50)
    )
    projects = result.all()

    if not projects:
        return {"suggested_tags": [], "project_count": 0}

    summaries = []
    for title, description in projects:
        desc_short = (description or "")[:200]
        summaries.append(f"- {title}: {desc_short}")

    user_prompt = "Проекты:\n" + "\n".join(summaries)

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=TAG_SUGGEST_SYSTEM,
            user_prompt=user_prompt,
            json_mode=True,
        )
        suggested = response.get("tags", [])
        suggested = [str(t).strip() for t in suggested if t and str(t).strip()]
        return {"suggested_tags": suggested, "project_count": len(projects)}
    except Exception:
        logger.exception("LLM tag suggestion failed")
        return {"suggested_tags": [], "project_count": len(projects)}


async def replace_tags(db: AsyncSession, tags: list[str]) -> dict:
    """Replace all tags with a new set. Returns added/removed/final lists."""
    cleaned = list(dict.fromkeys(t.strip() for t in tags if t and t.strip()))

    existing_map = await tag_repo.get_name_to_id_map(db)
    existing_names = set(existing_map.keys())
    new_names = set(cleaned)

    to_add = new_names - existing_names
    to_remove = existing_names - new_names

    added = []
    for name in sorted(to_add):
        await tag_repo.create(db, name)
        added.append(name)

    removed = []
    for name in sorted(to_remove):
        await tag_repo.delete_by_id(db, existing_map[name])
        removed.append(name)

    await db.commit()

    final_tags = await tag_repo.list_all(db)
    return {"final_tags": final_tags, "added": added, "removed": removed}
