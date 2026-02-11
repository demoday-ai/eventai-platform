"""Admin project list endpoints."""

import asyncio
import logging
import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas.admin import ProjectDetailResponse, ProjectListItem, ProjectUpdateRequest
from app.services.admin import admin_service, project_service
from app.services.core import user_service

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory tag generation progress store
_tag_generation_tasks: dict[str, dict] = {}


@router.get("/projects", response_model=list[ProjectListItem])
async def get_projects(
    room_id: UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get list of all projects with optional filters."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    return await admin_service.get_projects_list(db, event.id, room_id, status, search)


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project_detail(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed project view."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    result = await admin_service.get_project_detail(db, event.id, project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")

    return result


@router.patch("/projects/{project_id}", response_model=ProjectDetailResponse)
async def update_project(
    project_id: UUID,
    body: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update project title, description, or tags."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    result = await admin_service.update_project(db, event.id, project_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")

    return result


async def _run_tag_generation(task_id: str, event_id: UUID):
    """Background task for tag generation with progress tracking."""
    from app.database import async_session

    _tag_generation_tasks[task_id]["status"] = "running"

    try:
        async with async_session() as db:
            def progress_callback(progress: dict):
                # Check if task was cancelled
                if _tag_generation_tasks.get(task_id, {}).get("status") == "cancelled":
                    raise asyncio.CancelledError("Tag generation cancelled by user")

                _tag_generation_tasks[task_id].update({
                    "current": progress.get("current", 0),
                    "total": progress.get("total", 0),
                    "tagged": progress.get("tagged", 0),
                })

            result = await project_service.generate_missing_tags(
                db, event_id, progress_callback=progress_callback
            )
            _tag_generation_tasks[task_id].update({
                "status": "completed",
                "processed": result.get("processed", 0),
                "tagged": result.get("tagged", 0),
                "current": result.get("processed", 0),
                "total": result.get("processed", 0),
                "message": result.get("message"),
            })
    except asyncio.CancelledError:
        logger.info("Tag generation cancelled: task_id=%s", task_id)
        _tag_generation_tasks[task_id].update({
            "status": "cancelled",
            "error": "Генерация тегов отменена пользователем",
        })
    except Exception as e:
        logger.exception("Tag generation failed")
        _tag_generation_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
        })


@router.post("/projects/generate-tags")
async def generate_project_tags(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate tags for projects without tags using heuristic + LLM."""

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    # Check if there are projects without tags first (quick check)
    from sqlalchemy import func, select

    from app.models.project import Project
    from app.models.project_tag import ProjectTag

    stmt = (
        select(func.count(Project.id))
        .where(Project.event_id == event.id)
        .outerjoin(ProjectTag, ProjectTag.project_id == Project.id)
        .group_by(Project.id)
        .having(func.count(ProjectTag.id) == 0)
    )
    result = await db.execute(stmt)
    count = len(result.all())

    if count == 0:
        return {"processed": 0, "tagged": 0, "message": "All projects already have tags"}

    task_id = uuid_mod.uuid4().hex[:12]
    _tag_generation_tasks[task_id] = {
        "status": "pending",
        "current": 0,
        "total": count,
        "tagged": 0,
        "processed": 0,
    }

    asyncio.create_task(_run_tag_generation(task_id, event.id))

    return {"task_id": task_id, "status": "pending", "total": count}


@router.get("/projects/generate-tags/status/{task_id}")
async def get_tag_generation_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get tag generation progress."""

    task = _tag_generation_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.delete("/projects/generate-tags/{task_id}")
async def cancel_tag_generation(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel running tag generation task."""

    task = _tag_generation_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] not in ("running", "pending"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status: {task['status']}",
        )

    _tag_generation_tasks[task_id]["status"] = "cancelled"
    logger.info("Cancelling tag generation: task_id=%s", task_id)

    return {"status": "cancelled", "message": "Tag generation cancelled"}
