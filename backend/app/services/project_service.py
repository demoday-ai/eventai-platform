"""Project upload, validation, and query service."""

import csv
import io
import json
import logging
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.room_project import RoomProject
from app.models.tag import Tag
from app.schemas.project import ProjectUploadRow, RowError, UploadResult

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"title", "description", "tags", "author", "telegram_contact"}


def parse_csv(content: bytes) -> list[dict]:
    """Parse CSV content into list of row dicts."""
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def parse_json(content: bytes) -> list[dict]:
    """Parse JSON content (array of objects)."""
    return json.loads(content.decode("utf-8-sig"))


def validate_rows(rows: list[dict]) -> tuple[list[ProjectUploadRow], list[RowError], list[str]]:
    """Validate rows, returning (valid, errors, duplicate_titles)."""
    valid: list[ProjectUploadRow] = []
    errors: list[RowError] = []
    seen_titles: set[str] = set()
    duplicate_titles: list[str] = []

    for i, row in enumerate(rows, start=2):  # row 1 is header
        # Check required fields
        missing = REQUIRED_FIELDS - set(row.keys())
        if missing:
            for field in sorted(missing):
                errors.append(RowError(row=i, field=field, message="Обязательное поле отсутствует"))
            continue

        title = (row.get("title") or "").strip()
        if not title or len(title) < 3:
            errors.append(RowError(row=i, field="title", message="Название слишком короткое (мин. 3 символа)"))
            continue

        description = (row.get("description") or "").strip()
        if not description:
            errors.append(RowError(row=i, field="description", message="Описание обязательно"))
            continue

        author = (row.get("author") or "").strip()
        if not author:
            errors.append(RowError(row=i, field="author", message="Автор обязателен"))
            continue

        tg = (row.get("telegram_contact") or "").strip()
        if not tg:
            errors.append(RowError(row=i, field="telegram_contact", message="Telegram контакт обязателен"))
            continue

        if title in seen_titles:
            duplicate_titles.append(title)
            continue

        seen_titles.add(title)
        raw_tags = row.get("tags") or ""
        if isinstance(raw_tags, list):
            tags_str = ", ".join(raw_tags)
        else:
            tags_str = raw_tags.strip()
        valid.append(ProjectUploadRow(
            title=title,
            description=description[:2000],
            tags=tags_str,
            author=author,
            telegram_contact=tg,
        ))

    return valid, errors, duplicate_titles


async def save_projects(
    session: AsyncSession,
    event_id: uuid.UUID,
    rows: list[ProjectUploadRow],
) -> int:
    """Bulk insert projects with tag resolution. Returns count loaded."""
    tag_cache: dict[str, Tag] = {}
    loaded = 0

    for row in rows:
        project = Project(
            event_id=event_id,
            title=row.title,
            description=row.description,
            author=row.author,
            telegram_contact=row.telegram_contact,
            source="upload",
        )
        session.add(project)
        await session.flush()

        if row.tags:
            for tag_name in row.tags.split(","):
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

                pt = ProjectTag(project_id=project.id, tag_id=tag_cache[tag_name].id)
                session.add(pt)

        loaded += 1

    await session.commit()
    return loaded


async def get_projects(
    session: AsyncSession,
    event_id: uuid.UUID,
    room_id: uuid.UUID | None = None,
    search: str | None = None,
) -> list[Project]:
    """List projects with tags for given event."""
    stmt = (
        select(Project)
        .where(Project.event_id == event_id)
        .options(selectinload(Project.tags).selectinload(ProjectTag.tag))
        .options(selectinload(Project.room_assignments).selectinload(RoomProject.room))
        .order_by(Project.title)
    )

    if room_id:
        stmt = stmt.join(Project.room_assignments).where(RoomProject.room_id == room_id)

    if search:
        stmt = stmt.where(Project.title.ilike(f"%{search}%"))

    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_project_count(session: AsyncSession, event_id: uuid.UUID) -> int:
    """Count projects for event."""
    result = await session.scalar(
        select(func.count(Project.id)).where(Project.event_id == event_id)
    )
    return result or 0


async def delete_all_projects(session: AsyncSession, event_id: uuid.UUID) -> int:
    """Delete all projects for event (cascade deletes tags, room assignments)."""
    count = await get_project_count(session, event_id)
    await session.execute(
        delete(Project).where(Project.event_id == event_id)
    )
    await session.commit()
    return count
