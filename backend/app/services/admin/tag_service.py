"""Tag management service (split from admin_service)."""

import logging
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, Tag
from app.prompts.admin.tags import TAG_SUGGEST_SYSTEM, build_tag_suggest_prompt

logger = logging.getLogger(__name__)

# Single source of truth for tags and their descriptions
DEFAULT_TAGS = {
    "NLP": "Natural Language Processing (чат-боты, RAG, суммаризация)",
    "CV": "Computer Vision (детекция, сегментация, генерация картинок)",
    "ML": "Machine Learning (классическое машинное обучение)",
    "DL": "Deep Learning (глубокое обучение)",
    "LLM": "Large Language Models (файн-тюнинг, инференс)",
    "RAG": "Retrieval-Augmented Generation (поиск по документам)",
    "Agents": "Autonomous Agents (автономные агенты, мультиагентные системы)",
    "Recsys": "Recommender Systems (рекомендательные системы)",
    "EdTech": "Education Technology",
    "FinTech": "Financial Technology (антифрод, скоринг)",
    "MedTech": "Medical Technology (диагностика, drug discovery)",
    "AgriTech": "Agricultural Technology",
    "Security": "Information Security (детекция угроз)",
    "MLOps": "ML Operations",
    "ASR": "Automatic Speech Recognition (распознавание речи)",
    "TTS": "Text-to-Speech (синтез речи)",
    "RL": "Reinforcement Learning (обучение с подкреплением)",
    "TimeSeries": "Time Series Analysis (временные ряды)",
    "Backend": "Backend Development",
    "Industrial": "Industrial ML (предиктивное обслуживание, контроль качества)",
    "Other": "Other topics",
}

# Generate formatted tag list for prompts
_tag_list_with_desc = ", ".join(f"{k} ({v})" for k, v in DEFAULT_TAGS.items())
_tag_list_plain = ", ".join(DEFAULT_TAGS.keys())


async def list_tags(db: AsyncSession) -> list[str]:
    """List all available tags."""
    result = await db.execute(select(Tag.name).order_by(Tag.name))
    return [row[0] for row in result.all()]


async def add_tags(db: AsyncSession, tags: list[str]) -> tuple[list[str], list[str]]:
    """Add new tags (dedupe by lowercase). Returns (added, skipped)."""
    cleaned = [t.strip() for t in tags if t and t.strip()]
    if not cleaned:
        return [], []

    # Get existing tag names (lowercase for comparison)
    result = await db.execute(select(Tag.name))
    existing = {row[0].lower() for row in result.all()}

    added: list[str] = []
    skipped: list[str] = []
    for tag in cleaned:
        if tag.lower() in existing:
            skipped.append(tag)
            continue
        # Create new tag
        new_tag = Tag(name=tag)
        db.add(new_tag)
        await db.flush()
        existing.add(tag.lower())
        added.append(tag)

    if added:
        await db.commit()

    return added, skipped


async def seed_default_tags(db: AsyncSession) -> tuple[list[str], list[str]]:
    """Seed the default tag set. Returns (added, skipped)."""
    return await add_tags(db, list(DEFAULT_TAGS.keys()))


async def delete_tag(db: AsyncSession, tag_name: str) -> bool:
    """Delete a single tag and its project associations. Returns True if found."""
    result = await db.execute(select(Tag).where(Tag.name == tag_name))
    tag = result.scalar_one_or_none()
    if not tag:
        return False
    await db.delete(tag)
    await db.commit()
    return True


async def suggest_tags(db: AsyncSession, event_id: UUID) -> dict:
    """Analyze project descriptions and suggest tags via LLM."""
    from app.services.core import llm_client

    result = await db.execute(select(Project.title, Project.description).where(Project.event_id == event_id).limit(50))
    projects = result.all()

    if not projects:
        return {"suggested_tags": [], "project_count": 0}

    projects_data = [
        {"id": str(i), "title": title, "description": (description or "")[:200]}
        for i, (title, description) in enumerate(projects)
    ]

    system_prompt = TAG_SUGGEST_SYSTEM.format(available_tags=_tag_list_plain)
    user_prompt = build_tag_suggest_prompt(projects_data)

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=system_prompt,
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

    # Get existing tags as name->id map
    result = await db.execute(select(Tag.name, Tag.id))
    existing_map: dict[str, uuid.UUID] = {row[0]: row[1] for row in result.all()}
    existing_names = set(existing_map.keys())
    new_names = set(cleaned)

    to_add = new_names - existing_names
    to_remove = existing_names - new_names

    added = []
    for name in sorted(to_add):
        new_tag = Tag(name=name)
        db.add(new_tag)
        await db.flush()
        added.append(name)

    removed = []
    for name in sorted(to_remove):
        tag = await db.get(Tag, existing_map[name])
        if tag:
            await db.delete(tag)
            removed.append(name)

    await db.commit()

    # Get final list
    result = await db.execute(select(Tag.name).order_by(Tag.name))
    final_tags = [row[0] for row in result.all()]
    return {"final_tags": final_tags, "added": added, "removed": removed}
