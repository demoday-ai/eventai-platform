"""Expert matching endpoints: run, current, move, assign, approve."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.user import User
from app.schemas.expert import (
    ApproveResult,
    AssignExpertRequest,
    MatchingRequest,
    MoveExpertRequest,
)
from app.services.admin import matching_service

router = APIRouter()


@router.post("/matching/run")
async def run_matching_endpoint(
    body: MatchingRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Run expert-room matching. Uses Celery for async LLM processing."""
    from app.services.core import user_service
    from app.worker.tasks import run_matching_task
    from app.worker.utils import wait_for_task

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    use_adjacent = body.use_adjacent_tags if body else True

    # Submit to Celery and wait
    task = run_matching_task.delay(str(event.id), use_adjacent)
    completed, result = await wait_for_task(task.id, timeout=60, poll_interval=0.5)

    if not completed:
        raise HTTPException(status_code=504, detail="Matching timed out. Try again later.")

    if not result:
        raise HTTPException(status_code=500, detail="Failed to run matching.")

    # Check for error in result
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=409, detail=result["error"])

    return result


@router.get("/matching/current")
async def get_current_matching(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.services.core import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    result = await matching_service.get_current_matching(session, event.id)
    if not result:
        raise HTTPException(status_code=404, detail="No matching found")
    return result


@router.post("/matching/{assignment_id}/move")
async def move_expert_endpoint(
    assignment_id: uuid.UUID,
    body: MoveExpertRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    assignment = await matching_service.move_expert(session, assignment_id, body.target_room_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    return {
        "id": str(assignment.id),
        "expert_id": str(assignment.expert_id),
        "room_id": str(assignment.room_id),
        "room_name": assignment.room.name if assignment.room else "",
        "match_score": assignment.match_score,
        "is_manual": assignment.is_manual,
        "status": assignment.status,
    }


@router.post("/matching/assign")
async def assign_expert_endpoint(
    body: AssignExpertRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Manually assign an unmatched expert to a room."""
    from app.services.core import user_service

    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    assignment = await matching_service.assign_expert_to_room(
        session, event.id, body.expert_id, body.room_id
    )
    if not assignment:
        raise HTTPException(
            status_code=400,
            detail="Не удалось назначить. Эксперт уже назначен или зал не найден.",
        )

    return {
        "id": str(assignment.id),
        "expert_id": str(assignment.expert_id),
        "room_id": str(assignment.room_id),
        "room_name": assignment.room.name if assignment.room else "",
        "match_score": assignment.match_score,
        "is_manual": assignment.is_manual,
        "status": assignment.status,
    }


@router.post("/matching/approve")
async def approve_matching_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    from app.services.core import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    clustering = await matching_service.get_approved_clustering(session, event.id)
    if not clustering:
        raise HTTPException(status_code=404, detail="No approved clustering found")

    count = await matching_service.approve_matching(session, clustering.id)
    if count == 0:
        return ApproveResult(approved_count=0, message="All assignments already approved")

    return ApproveResult(approved_count=count, message=f"Approved {count} expert assignments")
