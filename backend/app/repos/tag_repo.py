"""Tag data access."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_tag import ProjectTag
from app.models.tag import Tag


async def list_all(session: AsyncSession) -> list[str]:
    """List all tag names, sorted alphabetically."""
    result = await session.execute(select(Tag.name).order_by(Tag.name))
    return [row[0] for row in result.all()]


async def get_existing_names(session: AsyncSession) -> set[str]:
    """Get set of existing tag names (lowercase)."""
    result = await session.execute(select(Tag.name))
    return {row[0].lower() for row in result.all()}


async def get_name_to_id_map(session: AsyncSession) -> dict[str, UUID]:
    """Get mapping of tag name → tag id."""
    result = await session.execute(select(Tag.id, Tag.name))
    return {row[1]: row[0] for row in result.all()}


async def create(session: AsyncSession, name: str) -> Tag:
    """Create a new tag."""
    tag = Tag(name=name)
    session.add(tag)
    return tag


async def get_by_name(session: AsyncSession, name: str) -> Tag | None:
    """Get a tag by exact name."""
    return await session.scalar(select(Tag).where(Tag.name == name))


async def delete_by_id(session: AsyncSession, tag_id: UUID) -> None:
    """Delete a tag and its project associations."""
    await session.execute(delete(ProjectTag).where(ProjectTag.tag_id == tag_id))
    await session.execute(delete(Tag).where(Tag.id == tag_id))


async def delete_by_name(session: AsyncSession, name: str) -> bool:
    """Delete a tag by name. Returns True if found and deleted."""
    tag = await get_by_name(session, name)
    if not tag:
        return False
    await delete_by_id(session, tag.id)
    return True
