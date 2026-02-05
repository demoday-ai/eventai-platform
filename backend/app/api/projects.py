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
    UploadResult,
)
from app.services import audit_service, clustering_service, dedup_service, project_service, user_service
from app.services.background_jobs import JobStatus, get_job, start_background_job

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


@router.post("/projects/upload", response_model=UploadResult)
async def upload_projects(
    file: UploadFile,
    replace: bool = False,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload projects from CSV or JSON file (organizer only)."""
    # Get current event
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    # Check organizer role
    role = await user_service.get_user_role_with_info(session, user.id, event.id)
    if not role or role.code != "organizer":
        raise HTTPException(status_code=403, detail="Только организатор может загружать проекты")

    # Check file format
    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".json")):
        raise HTTPException(
            status_code=400,
            detail="Поддерживаемые форматы: CSV, JSON",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Файл пуст")

    file_hash = dedup_service.compute_file_hash(content)
    dup_info = await dedup_service.check_recent_duplicate(session, file_hash, "upload_projects")

    # Parse
    try:
        if filename.endswith(".csv"):
            rows = project_service.parse_csv(content)
        else:
            rows = project_service.parse_json(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка парсинга файла: {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="Файл не содержит данных")

    # Validate
    valid, errors, duplicate_titles = project_service.validate_rows(rows)

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

    # Replace existing if requested
    if existing_count > 0 and replace:
        await project_service.delete_all_projects(session, event.id)

    # Save valid projects
    loaded = await project_service.save_projects(session, event.id, valid)

    logger.info("Upload: %d loaded, %d errors, %d duplicates", loaded, len(errors), len(duplicate_titles))

    await audit_service.log_action(
        session, user, "upload_projects",
        entity_type="projects",
        details={"loaded": loaded, "errors": len(errors), "duplicates": len(duplicate_titles), "file_hash": file_hash},
    )

    return UploadResult(
        loaded=loaded,
        errors=len(errors),
        duplicates=len(duplicate_titles),
        error_details=errors[:50],
        duplicate_titles=duplicate_titles[:20],
        duplicate_warning=dup_info["warning"] if dup_info else None,
    )


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
    """Run AI clustering (organizer only). Returns job_id for polling."""
    from app.database import async_session

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    role = await user_service.get_user_role_with_info(session, user.id, event.id)
    if not role or role.code != "organizer":
        raise HTTPException(status_code=403, detail="Только организатор может запускать кластеризацию")

    # Capture params for background job
    event_id = event.id
    num_rooms = request.num_rooms
    feedback = request.feedback

    async def do_clustering():
        """Run clustering in background with fresh DB session."""
        async with async_session() as bg_session:
            run = await clustering_service.run_clustering(
                bg_session, event_id, num_rooms, feedback
            )
            return {"run_id": str(run.id)}

    job = start_background_job(do_clustering())
    return {"job_id": job.id, "status": job.status.value}


@router.get("/clustering/job/{job_id}")
async def get_clustering_job_status(
    job_id: str,
    user: User = Depends(get_current_user),
):
    """Get clustering job status for polling."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job.id,
        "status": job.status.value,
    }

    if job.status == JobStatus.COMPLETED:
        response["result"] = job.result
    elif job.status == JobStatus.FAILED:
        response["error"] = job.error

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
    """Move project to another room (organizer only)."""
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    role = await user_service.get_user_role_with_info(session, user.id, event.id)
    if not role or role.code != "organizer":
        raise HTTPException(status_code=403, detail="Только организатор")

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
    """Approve clustering as schedule (organizer only)."""
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=400, detail="Нет активного события")

    role = await user_service.get_user_role_with_info(session, user.id, event.id)
    if not role or role.code != "organizer":
        raise HTTPException(status_code=403, detail="Только организатор")

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
