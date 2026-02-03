"""Load seed data from projects_seed.json into DB on first startup."""

import json
import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.tag import Tag

logger = logging.getLogger(__name__)

# In Docker: /app/data/seed/..., locally: relative to backend/
_BASE = Path("/app") if Path("/app/data").exists() else Path(__file__).resolve().parent.parent.parent.parent
SEED_FILE = _BASE / "data" / "seed" / "projects_seed.json"


async def load_seed_projects(session: AsyncSession, event_id) -> int:
    """Load seed projects into DB if none exist for the given event.

    Returns the number of projects loaded (0 if skipped).
    """
    count = await session.scalar(
        select(func.count(Project.id)).where(Project.event_id == event_id)
    )
    if count and count > 0:
        logger.info("Seed skipped: %d projects already exist for event %s", count, event_id)
        return 0

    if not SEED_FILE.exists():
        logger.warning("Seed file not found: %s", SEED_FILE)
        return 0

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    if not data:
        logger.warning("Seed file is empty")
        return 0

    # Build tag cache: name -> Tag object
    tag_cache: dict[str, Tag] = {}

    loaded = 0
    for item in data:
        title = item.get("title", "").strip()
        if not title:
            continue

        project = Project(
            event_id=event_id,
            title=title,
            description=item.get("description", f"Проект: {title}"),
            author=item.get("author", "Неизвестен"),
            telegram_contact=item.get("telegram_contact", "@unknown"),
            source="seed",
        )
        session.add(project)

        for tag_name in item.get("tags", []):
            tag_name = tag_name.strip()
            if not tag_name:
                continue

            if tag_name not in tag_cache:
                # Check if tag already exists in DB
                existing = await session.scalar(
                    select(Tag).where(Tag.name == tag_name)
                )
                if existing:
                    tag_cache[tag_name] = existing
                else:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                    await session.flush()
                    tag_cache[tag_name] = tag

            pt = ProjectTag(project_id=project.id, tag_id=tag_cache[tag_name].id)
            session.add(pt)

        loaded += 1

    await session.commit()
    logger.info("Seed loaded: %d projects into event %s", loaded, event_id)
    return loaded
