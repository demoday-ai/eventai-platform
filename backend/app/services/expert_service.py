"""Expert CRUD, seed loading, and upload."""

import json
import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expert import Expert
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.expert_tag import ExpertTag
from app.models.tag import Tag

logger = logging.getLogger(__name__)

# In Docker: /app/data/seed/..., locally: relative to backend/
_BASE = Path("/app") if Path("/app/data").exists() else Path(__file__).resolve().parent.parent.parent.parent
SEED_FILE = _BASE / "data" / "seed" / "experts_seed.json"


async def load_seed_experts(session: AsyncSession, event_id) -> int:
    """Load seed experts into DB if none exist for the given event."""
    count = await session.scalar(
        select(func.count(Expert.id)).where(Expert.event_id == event_id)
    )
    if count and count > 0:
        logger.info("Expert seed skipped: %d experts already exist for event %s", count, event_id)
        return 0

    if not SEED_FILE.exists():
        logger.warning("Expert seed file not found: %s", SEED_FILE)
        return 0

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    if not data:
        logger.warning("Expert seed file is empty")
        return 0

    # Build tag cache
    tag_cache: dict[str, Tag] = {}

    loaded = 0
    for item in data:
        seed_id = item.get("id", "").strip()
        name = item.get("name", "").strip()
        if not seed_id or not name:
            continue

        telegram = item.get("telegram", "").strip()
        # Strip @ if present
        if telegram.startswith("@"):
            telegram = telegram[1:]

        expert = Expert(
            seed_id=seed_id,
            name=name,
            telegram_username=telegram or None,
            position=item.get("position", "") or None,
            inviter=item.get("inviter") or None,
            dd_status_seed=item.get("dd_status", "") or None,
            event_id=event_id,
        )
        session.add(expert)
        await session.flush()

        for tag_name in item.get("expertise_tags", []):
            tag_name = tag_name.strip()
            if not tag_name:
                continue

            if tag_name not in tag_cache:
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

            et = ExpertTag(expert_id=expert.id, tag_id=tag_cache[tag_name].id)
            session.add(et)

        loaded += 1

    await session.commit()
    logger.info("Expert seed loaded: %d experts into event %s", loaded, event_id)
    return loaded


async def get_experts(
    session: AsyncSession,
    event_id,
    has_tags: bool | None = None,
    tag_name: str | None = None,
    search: str | None = None,
) -> list[Expert]:
    """List experts for event with optional filters."""
    query = (
        select(Expert)
        .where(Expert.event_id == event_id)
        .options(selectinload(Expert.tags).selectinload(ExpertTag.tag))
    )

    if search:
        pattern = f"%{search}%"
        query = query.where(
            Expert.name.ilike(pattern) | Expert.telegram_username.ilike(pattern)
        )

    result = await session.execute(query)
    experts = list(result.scalars().all())

    # Post-filter for tag conditions (complex joins not needed for 294 records)
    if has_tags is True:
        experts = [e for e in experts if len(e.tags) > 0]
    elif has_tags is False:
        experts = [e for e in experts if len(e.tags) == 0]

    if tag_name:
        experts = [
            e for e in experts
            if any(et.tag.name == tag_name for et in e.tags)
        ]

    return experts


async def get_expert_by_telegram(
    session: AsyncSession, event_id, username: str
) -> Expert | None:
    """Lookup expert by telegram username (case-insensitive)."""
    result = await session.execute(
        select(Expert)
        .where(Expert.event_id == event_id)
        .where(func.lower(Expert.telegram_username) == username.lower())
        .options(
            selectinload(Expert.tags).selectinload(ExpertTag.tag),
            selectinload(Expert.assignments).selectinload(ExpertRoomAssignment.room),
        )
    )
    return result.scalars().first()


async def get_expert_detail(session: AsyncSession, expert_id) -> Expert | None:
    """Get expert with tags and assignments."""
    result = await session.execute(
        select(Expert)
        .where(Expert.id == expert_id)
        .options(
            selectinload(Expert.tags).selectinload(ExpertTag.tag),
            selectinload(Expert.assignments).selectinload(ExpertRoomAssignment.room),
        )
    )
    return result.scalars().first()


async def sync_expert_tags(session: AsyncSession, expert: Expert, tag_names: list[str]) -> None:
    """Delete existing tags for expert and set new ones."""
    # Delete existing ExpertTag rows
    existing = await session.execute(
        select(ExpertTag).where(ExpertTag.expert_id == expert.id)
    )
    for et in existing.scalars().all():
        await session.delete(et)
    await session.flush()

    # Build tag cache and create new ExpertTag rows
    tag_cache: dict[str, Tag] = {}
    for tag_name in tag_names:
        tag_name = tag_name.strip()
        if not tag_name:
            continue
        if tag_name not in tag_cache:
            existing_tag = await session.scalar(
                select(Tag).where(Tag.name == tag_name)
            )
            if existing_tag:
                tag_cache[tag_name] = existing_tag
            else:
                tag = Tag(name=tag_name)
                session.add(tag)
                await session.flush()
                tag_cache[tag_name] = tag
        et = ExpertTag(expert_id=expert.id, tag_id=tag_cache[tag_name].id)
        session.add(et)


async def delete_all_experts(session: AsyncSession, event_id) -> int:
    """Delete all experts for an event (for replace flow)."""
    result = await session.execute(
        select(Expert).where(Expert.event_id == event_id)
    )
    experts = result.scalars().all()
    count = len(experts)
    for expert in experts:
        await session.delete(expert)
    await session.commit()
    return count
