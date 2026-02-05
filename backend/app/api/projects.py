"""Project upload, listing, clustering, and approval API endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.user import User
from app.schemas.project import (
    ClusteringRequest,
    MoveProjectRequest,
    ProjectResponse,
    ReplaceConfirmation,
    RoomSummary,
)
from app.services import audit_service, clustering_service, dedup_service, project_service, user_service
from app.services.background_jobs import (
    JobStatus,
    create_job,
    get_active_job_by_type,
    get_job,
    update_job,
    update_job_progress,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Projects"])


def _project_to_response(project) -> ProjectResponse:
    """Convert Project model to response schema."""
    tags = [pt.tag.name for pt in project.tags if pt.tag]
    room = None
    if project.room_assignments:
        ra = project.room_assignments[0]
        room = RoomSummary(id=ra.room.id, name=ra.room.name)

    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        tags=tags,
        author=project.author,
        telegram_contact=project.telegram_contact,
        source=project.source,
        room=room,
    )


@router.post("/projects/upload")
async def upload_projects(
    file: UploadFile,
    replace: bool = False,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload projects from CSV or JSON file (organizer only). Returns job_id for polling."""
    from app.database import async_session

    # Get current event
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    # Check for already running upload job
    existing_job = get_active_job_by_type("project_upload")
    if existing_job:
        return {"job_id": existing_job.id, "status": existing_job.status.value}

    # Check file format
    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".json", ".xlsx")):
        raise HTTPException(
            status_code=400,
            detail="Поддерживаемые форматы: CSV, JSON, XLSX",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Файл пуст")

    # Parse and validate synchronously (fast operations)
    try:
        if filename.endswith(".csv"):
            rows = project_service.parse_csv(content)
        elif filename.endswith(".xlsx"):
            rows = project_service.parse_xlsx(content)
        else:
            rows = project_service.parse_json(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка парсинга файла: {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="Файл не содержит данных")

    valid, errors, duplicate_titles = project_service.validate_rows(rows)

    if not valid:
        raise HTTPException(status_code=400, detail={
            "message": "Нет валидных записей",
            "errors": [e.model_dump() for e in errors[:20]],
        })

    # Check for existing projects (replace flow)
    existing_count = await project_service.get_project_count(session, event.id)
    if existing_count > 0 and not replace:
        raise HTTPException(
            status_code=409,
            detail=ReplaceConfirmation(
                message=f"Заменить предыдущие данные ({existing_count} проектов) новыми ({len(valid)} проектов)?",
                existing_count=existing_count,
                new_count=len(valid),
            ).model_dump(),
        )

    # Capture data for background job
    event_id = event.id
    user_id = user.id
    file_hash = dedup_service.compute_file_hash(content)

    async def do_upload(job_id: str):
        """Run upload in background with fresh DB session."""
        async with async_session() as bg_session:
            # Delete existing if replacing
            if existing_count > 0 and replace:
                update_job_progress(job_id, {"stage": "deleting", "current": 0, "total": existing_count})
                await project_service.delete_all_projects(bg_session, event_id)
                await clustering_service.invalidate_clustering_runs(bg_session, event_id)

            # Save projects with progress tracking
            def progress_cb(progress):
                update_job_progress(job_id, progress)

            stats = await project_service.save_projects(
                bg_session, event_id, valid, progress_callback=progress_cb
            )

            # Log audit
            bg_user = await bg_session.get(User, user_id)
            if bg_user:
                await audit_service.log_action(
                    bg_session, bg_user, "upload_projects",
                    entity_type="projects",
                    details={
                        "loaded": stats["loaded"],
                        "tags_generated": stats["tags_generated"],
                        "errors": len(errors),
                        "duplicates": len(duplicate_titles),
                        "file_hash": file_hash,
                    },
                )

            return {
                "loaded": stats["loaded"],
                "tags_generated": stats["tags_generated"],
                "errors": len(errors),
                "duplicates": len(duplicate_titles),
                "error_details": [e.model_dump() for e in errors[:50]],
                "duplicate_titles": duplicate_titles[:20],
            }

    import asyncio

    job = create_job(job_type="project_upload")
    asyncio.create_task(_run_upload_job(job.id, do_upload))

    return {
        "job_id": job.id,
        "status": job.status.value,
        "total": len(valid),
    }


async def _run_upload_job(job_id: str, coro_factory):
    """Helper to run upload job with job_id passed to the coroutine."""
    update_job(job_id, JobStatus.RUNNING)
    try:
        result = await coro_factory(job_id)
        update_job(job_id, JobStatus.COMPLETED, result=result)
        logger.info(f"Upload job {job_id} completed successfully")
    except Exception as e:
        logger.exception(f"Upload job {job_id} failed: {e}")
        update_job(job_id, JobStatus.FAILED, error=str(e))


@router.get("/projects/upload/job/{job_id}")
async def get_upload_job_status(
    job_id: str,
    user: User = Depends(get_current_user),
):
    """Get project upload job status for polling."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job.id,
        "status": job.status.value,
        "progress": job.progress,
    }

    if job.status == JobStatus.COMPLETED:
        response["result"] = job.result
    elif job.status == JobStatus.FAILED:
        response["error"] = job.error

    return response


@router.get("/projects")
async def list_projects(
    room_id: uuid.UUID | None = None,
    search: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List projects for current event with optional filters."""
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    projects = await project_service.get_projects(session, event.id, room_id, search)

    return {
        "total": len(projects),
        "projects": [_project_to_response(p) for p in projects],
    }


@router.post("/clustering/run")
async def run_clustering(
    request: ClusteringRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Run AI clustering (organizer only). Returns job_id for polling.

    Uses Celery for distributed task processing.
    """
    from app.worker.tasks import cluster_projects_task

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    # Check for already running clustering job (legacy check)
    existing_job = get_active_job_by_type("clustering")
    if existing_job:
        return {"job_id": existing_job.id, "status": existing_job.status.value}

    if request.room_themes is not None and len(request.room_themes) != request.num_rooms:
        raise HTTPException(
            status_code=422,
            detail="room_themes length must match num_rooms",
        )

    # Submit to Celery
    task = cluster_projects_task.delay(
        str(event.id),
        request.num_rooms,
        request.feedback,
        request.room_themes,
    )

    return {"job_id": task.id, "status": "pending"}


@router.get("/clustering/job/{job_id}")
async def get_clustering_job_status(
    job_id: str,
    user: User = Depends(get_current_user),
):
    """Get clustering job status for polling.

    Supports both legacy background jobs and Celery tasks.
    """
    from app.worker.utils import get_task_status

    # First try legacy background job system
    job = get_job(job_id)
    if job:
        response = {
            "job_id": job.id,
            "status": job.status.value,
        }
        if job.status == JobStatus.COMPLETED:
            response["result"] = job.result
        elif job.status == JobStatus.FAILED:
            response["error"] = job.error
        return response

    # Try Celery task
    celery_status = get_task_status(job_id)
    if celery_status["status"] == "unknown":
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job_id,
        "status": celery_status["status"],
    }

    if celery_status["status"] == "completed":
        response["result"] = celery_status.get("result")
    elif celery_status["status"] == "failed":
        response["error"] = celery_status.get("error")

    return response


@router.get("/clustering/current")
async def get_current_clustering(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get current clustering result."""
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    run = await clustering_service.get_current_clustering(session, event.id)
    if not run:
        raise HTTPException(status_code=404, detail="Кластеризация не найдена")

    return _clustering_to_response(run)


@router.post("/clustering/{run_id}/move")
async def move_project(
    run_id: uuid.UUID,
    request: MoveProjectRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Move project to another room."""
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    try:
        await clustering_service.move_project(
            session, run_id, request.project_id, request.target_room_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    run = await clustering_service.get_clustering_run(session, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Кластеризация не найдена")

    return _clustering_to_response(run)


@router.post("/clustering/{run_id}/approve")
async def approve_clustering(
    run_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Approve clustering as schedule."""
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    try:
        result = await clustering_service.approve_clustering(session, run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result == "already_approved":
        raise HTTPException(
            status_code=409,
            detail={"message": "Расписание уже утверждено", "current_status": "approved"},
        )

    return {"status": "approved"}


def _clustering_to_response(run) -> dict:
    """Convert ClusteringRun to API response dict."""
    rooms = []
    for room in sorted(run.rooms, key=lambda r: r.display_order):
        projects = []
        for rp in room.project_assignments:
            p = rp.project
            tags = []
            if hasattr(p, "tags") and p.tags:
                tags = [pt.tag.name for pt in p.tags if pt.tag]
            projects.append(ProjectResponse(
                id=p.id,
                title=p.title,
                description=p.description,
                tags=tags,
                author=p.author,
                telegram_contact=p.telegram_contact,
                source=p.source,
            ))

        rooms.append({
            "id": room.id,
            "name": room.name,
            "theme_rationale": room.theme_rationale,
            "project_count": len(room.project_assignments),
            "projects": projects,
        })

    return {
        "id": run.id,
        "status": run.status,
        "num_rooms": run.num_rooms,
        "feedback": run.feedback,
        "rooms": rooms,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "approved_at": run.approved_at.isoformat() if run.approved_at else None,
    }
