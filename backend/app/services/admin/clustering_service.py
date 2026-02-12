"""AI clustering service: build prompts, run LLM, save results."""

import logging
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.clustering_run import ClusteringRun
from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.room import Room
from app.models.room_project import RoomProject
from app.prompts.admin.clustering import (
    CLUSTERING_SYSTEM,
    SUGGEST_THEMES_SYSTEM,
    build_clustering_prompt,
    build_suggest_themes_prompt,
)
from app.services.core import llm_client

logger = logging.getLogger(__name__)

# Sample size for Phase 1 (theme suggestion)
THEME_ANALYSIS_SAMPLE_SIZE = 100


async def suggest_room_themes(
    session: AsyncSession,
    event_id: uuid.UUID,
    num_rooms: int,
) -> list[str]:
    """Suggest room themes based on project tags and descriptions.

    Analyzes all projects using LLM and returns suggested theme names.
    Returns list[str] of length num_rooms.
    """
    # 1. Fetch projects with tags
    stmt = (
        select(Project)
        .where(Project.event_id == event_id)
        .options(selectinload(Project.tags).selectinload(ProjectTag.tag))
    )
    result = await session.execute(stmt)
    projects = list(result.scalars().unique().all())

    if len(projects) < 2:
        raise ValueError(f"Недостаточно проектов для анализа: {len(projects)}")

    # 2. Sample projects for analysis (limit context size)
    sample_size = min(THEME_ANALYSIS_SAMPLE_SIZE, len(projects))
    sampled_projects = random.sample(projects, sample_size) if len(projects) > sample_size else projects

    # 3. Build data for LLM (tags + descriptions)
    projects_data = []
    for p in sampled_projects:
        tags = [pt.tag.name for pt in p.tags if pt.tag]
        projects_data.append(
            {
                "id": str(p.id),
                "title": p.title,
                "tags": tags,
                "description": p.description[:500],
            }
        )

    # 4. Build prompt
    system_prompt = SUGGEST_THEMES_SYSTEM
    user_prompt = build_suggest_themes_prompt(projects_data, num_rooms)

    # 5. Call LLM (use fast model — this is a sync endpoint with gateway timeout)
    logger.info("Suggesting themes: %d sampled projects → %d rooms", sample_size, num_rooms)
    llm_response = await llm_client.send_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_mode=True,
        model="openai/gpt-4o-mini",
    )

    # 6. Validate response
    themes = llm_response.get("themes", [])
    if not themes or len(themes) != num_rooms:
        logger.warning("LLM returned %d themes, expected %d", len(themes), num_rooms)
        # Fallback to generic themes
        return [f"Зал {i + 1}" for i in range(num_rooms)]

    return themes


async def run_clustering(
    session: AsyncSession,
    event_id: uuid.UUID,
    num_rooms: int = 6,
    feedback: str | None = None,
    room_themes: list[str] | None = None,
) -> ClusteringRun:
    """Run AI clustering for projects in an event.

    1. Fetch all projects
    2. Build prompt
    3. Call LLM
    4. Validate response
    5. Save ClusteringRun + Rooms + RoomProjects
    6. Supersede previous draft runs
    """
    # 1. Fetch projects
    stmt = (
        select(Project)
        .where(Project.event_id == event_id)
        .options(selectinload(Project.tags).selectinload(ProjectTag.tag))
    )
    result = await session.execute(stmt)
    projects = list(result.scalars().unique().all())

    if len(projects) < 2:
        raise ValueError(f"Недостаточно проектов для кластеризации: {len(projects)}")

    # 2. Build prompt data
    projects_data = []
    project_map = {}
    for p in projects:
        pid = str(p.id)
        tags = [pt.tag.name for pt in p.tags if pt.tag]
        projects_data.append(
            {
                "id": pid,
                "title": p.title,
                "tags": tags,
                "description": p.description[:500],  # increased from 200 for better context
            }
        )
        project_map[pid] = p

    user_prompt = build_clustering_prompt(projects_data, num_rooms, feedback, room_themes=room_themes)

    # 3. Call LLM
    logger.info("Running clustering: %d projects → %d rooms", len(projects), num_rooms)
    llm_response = await llm_client.send_chat_completion(
        system_prompt=CLUSTERING_SYSTEM,
        user_prompt=user_prompt,
        json_mode=True,
    )

    # 4. Validate response
    rooms_data = llm_response.get("rooms", [])
    if not rooms_data:
        raise ValueError("LLM вернул пустой список залов")

    # Check all projects assigned exactly once
    assigned_ids = set()
    for room_data in rooms_data:
        for pid in room_data.get("project_ids", []):
            if pid in assigned_ids:
                logger.warning("Duplicate project assignment: %s", pid)
            assigned_ids.add(pid)

    all_project_ids = set(project_map.keys())
    missing = all_project_ids - assigned_ids
    if missing:
        logger.warning("Projects missing from clustering: %s", list(missing))
        if rooms_data:
            smallest = min(rooms_data, key=lambda r: len(r.get("project_ids", [])))
            smallest.setdefault("project_ids", []).extend(list(missing))
            logger.info("Added %d missing projects to smallest room '%s'", len(missing), smallest.get("name"))

    # 5. Supersede previous draft runs
    await session.execute(
        update(ClusteringRun)
        .where(
            ClusteringRun.event_id == event_id,
            ClusteringRun.status == "draft",
        )
        .values(status="superseded")
    )

    # 6. Save new run
    run = ClusteringRun(
        event_id=event_id,
        num_rooms=len(rooms_data),
        status="draft",
        feedback=feedback,
        llm_model=settings.openrouter_model,
    )
    session.add(run)
    await session.flush()

    assigned_project_ids: set[uuid.UUID] = set()
    for i, room_data in enumerate(rooms_data):
        room = Room(
            clustering_run_id=run.id,
            name=room_data.get("name", f"Зал {i + 1}"),
            theme_rationale=room_data.get("theme_rationale", ""),
            display_order=i,
        )
        session.add(room)
        await session.flush()

        for pid in room_data.get("project_ids", []):
            if pid in project_map:
                project_uuid = project_map[pid].id
                if project_uuid not in assigned_project_ids:
                    assigned_project_ids.add(project_uuid)
                    rp = RoomProject(
                        room_id=room.id,
                        project_id=project_uuid,
                        is_manual=False,
                    )
                    session.add(rp)

    await session.commit()

    # Reload with relationships
    return await get_clustering_run(session, run.id)


async def get_clustering_run(session: AsyncSession, run_id: uuid.UUID) -> ClusteringRun | None:
    """Get a clustering run with rooms and project assignments."""
    stmt = (
        select(ClusteringRun)
        .where(ClusteringRun.id == run_id)
        .options(
            selectinload(ClusteringRun.rooms)
            .selectinload(Room.project_assignments)
            .selectinload(RoomProject.project)
            .selectinload(Project.tags)
            .selectinload(ProjectTag.tag)
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_current_clustering(session: AsyncSession, event_id: uuid.UUID) -> ClusteringRun | None:
    """Get the latest clustering run for an event (draft or approved)."""
    stmt = (
        select(ClusteringRun)
        .where(
            ClusteringRun.event_id == event_id,
            ClusteringRun.status.in_(["draft", "approved"]),
        )
        .order_by(ClusteringRun.created_at.desc())
        .limit(1)
        .options(
            selectinload(ClusteringRun.rooms)
            .selectinload(Room.project_assignments)
            .selectinload(RoomProject.project)
            .selectinload(Project.tags)
            .selectinload(ProjectTag.tag)
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_room_details(session: AsyncSession, room_id: uuid.UUID) -> tuple:
    """Get room with its projects (including tags)."""
    stmt = (
        select(Room)
        .where(Room.id == room_id)
        .options(
            selectinload(Room.project_assignments)
            .selectinload(RoomProject.project)
            .selectinload(Project.tags)
            .selectinload(ProjectTag.tag)
        )
    )
    result = await session.execute(stmt)
    room = result.scalar_one_or_none()

    if not room:
        return None, []

    projects = [rp.project for rp in room.project_assignments]
    return room, projects


async def move_project(
    session: AsyncSession,
    run_id: uuid.UUID,
    project_id: uuid.UUID,
    target_room_id: uuid.UUID,
) -> None:
    """Move a project from its current room to a target room."""
    # Validate target room belongs to the requested run
    stmt = select(Room).where(
        Room.id == target_room_id,
        Room.clustering_run_id == run_id,
    )
    result = await session.execute(stmt)
    target_room = result.scalar_one_or_none()
    if not target_room:
        raise ValueError("Целевой зал не найден в данной кластеризации")

    # Find current assignment
    stmt = (
        select(RoomProject)
        .join(Room)
        .where(
            Room.clustering_run_id == run_id,
            RoomProject.project_id == project_id,
        )
    )
    result = await session.execute(stmt)
    current = result.scalar_one_or_none()

    if current:
        if current.room_id == target_room_id:
            raise ValueError("Проект уже в этом зале")
        await session.delete(current)

    # Create new assignment
    new_rp = RoomProject(
        room_id=target_room_id,
        project_id=project_id,
        is_manual=True,
    )
    session.add(new_rp)
    await session.commit()


async def approve_clustering(session: AsyncSession, run_id: uuid.UUID) -> str:
    """Approve a clustering run. Returns 'approved' or 'already_approved'."""
    run = await session.get(ClusteringRun, run_id)
    if not run:
        raise ValueError("Кластеризация не найдена")

    if run.status == "approved":
        return "already_approved"

    # Supersede other approved runs for this event
    await session.execute(
        update(ClusteringRun)
        .where(
            ClusteringRun.event_id == run.event_id,
            ClusteringRun.status == "approved",
            ClusteringRun.id != run_id,
        )
        .values(status="superseded")
    )

    run.status = "approved"
    run.approved_at = datetime.now(timezone.utc)
    await session.commit()

    return "approved"


async def invalidate_clustering_runs(session: AsyncSession, event_id: uuid.UUID) -> int:
    """Invalidate all clustering runs for an event (when projects are replaced).

    Returns count of invalidated runs.
    """
    result = await session.execute(
        update(ClusteringRun)
        .where(
            ClusteringRun.event_id == event_id,
            ClusteringRun.status.in_(["draft", "approved"]),
        )
        .values(status="superseded")
    )
    await session.commit()
    return result.rowcount or 0
