"""AI clustering service: build prompts, run LLM, save results."""

import json
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
from app.services.core import llm_client

logger = logging.getLogger(__name__)

# Sample size for Phase 1 (theme suggestion)
THEME_ANALYSIS_SAMPLE_SIZE = 100

SYSTEM_PROMPT = """Ты AI-ассистент для организации Demo Day. Твоя задача — распределить проекты по тематическим залам.

Constraints:
- Каждый проект должен быть ровно в одном зале
- Разница между самым большим и маленьким залом ≤ 5 проектов
- Группируй по тематической близости (NLP, CV, Agents, EdTech, FinTech и т.д.)
- Для каждого зала дай краткое название темы и обоснование (2-3 предложения)
- Названия залов должны быть информативными, например: "NLP и языковые модели", "Автономные агенты"

Верни JSON строго в формате:
{
  "rooms": [
    {
      "name": "Название темы зала",
      "theme_rationale": "Обоснование тематики зала (2-3 предложения)",
      "project_ids": ["id1", "id2", ...]
    }
  ]
}"""

SUGGEST_THEMES_SYSTEM_PROMPT = """Ты AI-ассистент для организации Demo Day.
Твоя задача — предложить тематики залов на основе анализа проектов.

Проанализируй теги и описания проектов, выяви основные тематические кластеры
(NLP, CV, Agents, EdTech, FinTech, Healthcare, etc).

Constraints:
- Количество тем должно быть ровно равно запрошенному числу залов
- Темы должны быть информативными и отражать содержание проектов (не "Зал 1", "Зал 2")
- Темы должны охватывать все проекты (не создавай слишком узкие темы)
- Учитывай И теги, И descriptions проектов (теги могут быть неполными)

Примеры хороших тем:
- "NLP и языковые модели"
- "Автономные агенты и RAG"
- "Computer Vision и мультимодальные модели"
- "AI в образовании и EdTech"
- "FinTech и предиктивная аналитика"

Верни JSON строго в формате:
{
  "themes": ["Тема зала 1", "Тема зала 2", ...]
}"""

ASSIGNMENT_SYSTEM_PROMPT = """Ты AI-ассистент для организации Demo Day.
Твоя задача — распределить проекты по заданным тематическим залам.

Constraints:
- Каждый проект должен быть ровно в одном зале
- Разница между самым большим и маленьким залом ≤ 5 проектов
- Группируй проекты по тематической близости к названию зала
- Используй теги и названия проектов для определения соответствия

Верни JSON строго в формате:
{
  "rooms": [
    {
      "name": "Название зала (из списка предложенных тем)",
      "project_ids": ["id1", "id2", ...]
    }
  ]
}"""


def _build_user_prompt(
    projects: list[dict],
    num_rooms: int,
    feedback: str | None = None,
    room_themes: list[str] | None = None,
) -> str:
    """Build the user prompt for clustering."""
    prompt = f"Распредели {len(projects)} проектов по {num_rooms} залам.\n\n"
    if room_themes:
        themes = ", ".join(room_themes)
        prompt += f"Тематики залов заданы организатором: {themes}.\n"
        prompt += "Используй эти тематики как названия залов и ориентиры для распределения.\n\n"
    prompt += "Проекты:\n"
    prompt += json.dumps(projects, ensure_ascii=False, indent=None)

    if feedback:
        prompt += f"\n\nФидбэк организатора: {feedback}"

    prompt += "\n\nВерни JSON с распределением."
    return prompt


def _build_suggest_themes_user_prompt(
    projects: list[dict],
    num_rooms: int,
) -> str:
    """Build user prompt for theme suggestion."""
    prompt = f"Предложи {num_rooms} тематик для залов на основе {len(projects)} проектов.\n\n"
    prompt += "Проекты:\n"
    prompt += json.dumps(projects, ensure_ascii=False, indent=None)
    prompt += "\n\nВерни JSON со списком тем."
    return prompt


def _build_assignment_user_prompt(
    projects: list[dict],
    room_themes: list[str],
) -> str:
    """Build user prompt for project assignment (compact format)."""
    prompt = f"Распредели {len(projects)} проектов по {len(room_themes)} залам.\n\n"
    prompt += f"Темы залов: {json.dumps(room_themes, ensure_ascii=False)}\n\n"
    prompt += "Проекты (id, title, tags):\n"
    # Compact format: only id, title, tags (no descriptions)
    compact_projects = [{"id": p["id"], "title": p["title"], "tags": p.get("tags", [])} for p in projects]
    prompt += json.dumps(compact_projects, ensure_ascii=False, indent=None)
    prompt += "\n\nВерни JSON с распределением проектов по залам."
    return prompt


async def suggest_room_themes(
    session: AsyncSession,
    event_id: uuid.UUID,
    num_rooms: int,
) -> list[str]:
    """Suggest room themes based on project tags and descriptions.

    Analyzes a sample of projects using LLM and returns suggested theme names.
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
    system_prompt = SUGGEST_THEMES_SYSTEM_PROMPT
    user_prompt = _build_suggest_themes_user_prompt(projects_data, num_rooms)

    # 5. Call LLM
    logger.info(
        "Suggesting themes: %d sampled projects (of %d total) → %d rooms", sample_size, len(projects), num_rooms
    )
    llm_response = await llm_client.send_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_mode=True,
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
    """Run two-phase AI clustering for projects in an event.

    Phase 1: Theme suggestion (if themes not provided)
      - Sample projects and suggest themes based on analysis
    Phase 2: Project assignment
      - Assign ALL projects to themes using compact prompt (no descriptions)

    Steps:
    1. Fetch all projects
    2. Phase 1: Suggest themes (if not provided)
    3. Phase 2: Assign projects to themes
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

    # 2. Phase 1: Suggest themes (if not provided)
    if not room_themes:
        logger.info("Phase 1: Suggesting themes for %d projects → %d rooms", len(projects), num_rooms)
        room_themes = await suggest_room_themes(session, event_id, num_rooms)
        logger.info("Phase 1 complete: themes = %s", room_themes)
    else:
        logger.info("Using provided themes: %s", room_themes)

    # 3. Build compact project data (no descriptions for Phase 2)
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
            }
        )
        project_map[pid] = p

    # 4. Phase 2: Assign projects to themes
    user_prompt = _build_assignment_user_prompt(projects_data, room_themes)

    logger.info("Phase 2: Assigning %d projects to %d themes", len(projects), len(room_themes))
    llm_response = await llm_client.send_chat_completion(
        system_prompt=ASSIGNMENT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        json_mode=True,
    )
    logger.info("Phase 2 complete")

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
        room_name = room_data.get("name", f"Зал {i + 1}")
        # Generate simple rationale if not provided by LLM
        theme_rationale = room_data.get("theme_rationale", "")
        if not theme_rationale:
            theme_rationale = f"Проекты по теме: {room_name}"

        room = Room(
            clustering_run_id=run.id,
            name=room_name,
            theme_rationale=theme_rationale,
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
