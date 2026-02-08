"""Project data access."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.tag import Tag


async def get_by_id(session: AsyncSession, project_id: UUID) -> Project | None:
    return await session.get(Project, project_id)


async def count_by_event(session: AsyncSession, event_id: UUID) -> int:
    return await session.scalar(
        select(func.count(Project.id)).where(Project.event_id == event_id)
    ) or 0


async def get_project_tags(session: AsyncSession, project_id: UUID) -> list[str]:
    """Get tag names for a project."""
    result = await session.execute(
        select(Tag.name)
        .select_from(ProjectTag)
        .join(Tag, ProjectTag.tag_id == Tag.id)
        .where(ProjectTag.project_id == project_id)
    )
    return [row[0] for row in result.all()]


async def get_projects_with_descriptions(
    session: AsyncSession, event_id: UUID, limit: int = 50
) -> list[tuple[str, str | None]]:
    """Get project (title, description) pairs for LLM analysis."""
    result = await session.execute(
        select(Project.title, Project.description)
        .where(Project.event_id == event_id)
        .limit(limit)
    )
    return list(result.all())
