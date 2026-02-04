"""Expert management, matching, invites, coverage, and escalation endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models.user import User
from app.schemas.expert import (
    ApproveResult,
    ExpertCreateRequest,
    ExpertDetailResponse,
    ExpertResponse,
    ExpertUpdateRequest,
    MatchingRequest,
    MoveExpertRequest,
)
from app.services import coverage_service, expert_service, invite_service, matching_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["experts"])


def _require_organizer(user: User):
    if str(user.telegram_user_id) not in settings.organizer_ids:
        raise HTTPException(status_code=403, detail="Organizer access required")


def _expert_to_response(expert) -> ExpertResponse:
    tags = [et.tag.name for et in expert.tags] if expert.tags else []
    status = None
    if expert.assignments:
        status = expert.assignments[0].status
    return ExpertResponse(
        id=expert.id,
        seed_id=expert.seed_id,
        name=expert.name,
        telegram_username=expert.telegram_username,
        position=expert.position,
        tags=tags,
        bot_started=expert.bot_started,
        assignment_status=status,
    )


@router.post("/experts/upload")
async def upload_experts(
    file: UploadFile = File(...),
    confirm_replace: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    # Check existing experts
    from sqlalchemy import func, select
    from app.models.expert import Expert

    count = await session.scalar(
        select(func.count(Expert.id)).where(Expert.event_id == event.id)
    )

    if count and count > 0 and not confirm_replace:
        return {"existing_count": count, "message": f"{count} experts already exist. Set confirm_replace=true to replace."}

    if count and count > 0 and confirm_replace:
        await expert_service.delete_all_experts(session, event.id)

    # Parse uploaded file
    import json
    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Expected JSON array")

    # Use seed loading logic
    from app.models.tag import Tag
    from app.models.expert_tag import ExpertTag as ExpertTagModel

    tag_cache: dict[str, object] = {}
    imported = 0
    with_tags = 0
    without_tags = 0
    errors = []

    for i, item in enumerate(data):
        seed_id = item.get("id", "").strip() if isinstance(item.get("id"), str) else str(item.get("id", ""))
        name = item.get("name", "").strip()
        if not seed_id or not name:
            errors.append({"row": i, "field": "id/name", "message": "Missing required field"})
            continue

        telegram = item.get("telegram", "").strip()
        if telegram.startswith("@"):
            telegram = telegram[1:]

        tags_list = item.get("expertise_tags", [])
        if tags_list:
            with_tags += 1
        else:
            without_tags += 1

        expert = Expert(
            seed_id=seed_id,
            name=name,
            telegram_username=telegram or None,
            position=item.get("position", "") or None,
            inviter=item.get("inviter") or None,
            dd_status_seed=item.get("dd_status", "") or None,
            event_id=event.id,
        )
        session.add(expert)
        await session.flush()

        for tag_name in tags_list:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            if tag_name not in tag_cache:
                existing = await session.scalar(select(Tag).where(Tag.name == tag_name))
                if existing:
                    tag_cache[tag_name] = existing
                else:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                    await session.flush()
                    tag_cache[tag_name] = tag
            et = ExpertTagModel(expert_id=expert.id, tag_id=tag_cache[tag_name].id)
            session.add(et)

        imported += 1

    await session.commit()

    return {
        "total_parsed": len(data),
        "imported": imported,
        "with_tags": with_tags,
        "without_tags": without_tags,
        "errors": errors,
    }


@router.post("/experts")
async def create_expert(
    body: ExpertCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    from app.models.expert import Expert

    telegram = body.telegram_username
    if telegram and telegram.startswith("@"):
        telegram = telegram[1:]

    expert = Expert(
        seed_id=f"manual-{uuid.uuid4().hex[:8]}",
        name=body.name,
        telegram_username=telegram or None,
        position=body.position or None,
        event_id=event.id,
    )
    session.add(expert)
    await session.flush()

    if body.tags:
        await expert_service.sync_expert_tags(session, expert, body.tags)

    await session.commit()

    # Reload with tags
    expert = await expert_service.get_expert_detail(session, expert.id)
    return _expert_to_response(expert)


@router.patch("/experts/{expert_id}")
async def update_expert(
    expert_id: uuid.UUID,
    body: ExpertUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    expert = await expert_service.get_expert_detail(session, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    if body.name is not None:
        expert.name = body.name
    if body.telegram_username is not None:
        telegram = body.telegram_username
        if telegram.startswith("@"):
            telegram = telegram[1:]
        expert.telegram_username = telegram or None
    if body.position is not None:
        expert.position = body.position or None

    if body.tags is not None:
        await expert_service.sync_expert_tags(session, expert, body.tags)

    await session.commit()

    # Reload with tags
    expert = await expert_service.get_expert_detail(session, expert_id)
    return _expert_to_response(expert)


@router.get("/experts")
async def list_experts(
    has_tags: bool | None = Query(None),
    tag: str | None = Query(None),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    experts = await expert_service.get_experts(
        session, event.id, has_tags=has_tags, tag_name=tag, search=search
    )
    return [_expert_to_response(e) for e in experts]


@router.get("/experts/{expert_id}")
async def get_expert(
    expert_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    expert = await expert_service.get_expert_detail(session, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    resp = _expert_to_response(expert)
    return ExpertDetailResponse(
        **resp.model_dump(),
        inviter=expert.inviter,
        dd_status_seed=expert.dd_status_seed,
        assignment=None,
    )


@router.post("/matching/run")
async def run_matching_endpoint(
    body: MatchingRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    use_adjacent = body.use_adjacent_tags if body else True

    try:
        result = await matching_service.run_matching(session, event.id, use_adjacent_tags=use_adjacent)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return result


@router.get("/matching/current")
async def get_current_matching(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.services import user_service
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
    _require_organizer(current_user)

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


@router.post("/matching/approve")
async def approve_matching_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    clustering = await matching_service.get_approved_clustering(session, event.id)
    if not clustering:
        raise HTTPException(status_code=404, detail="No approved clustering found")

    count = await matching_service.approve_matching(session, clustering.id)
    if count == 0:
        raise HTTPException(status_code=404, detail="No proposed assignments to approve")

    return ApproveResult(approved_count=count, message=f"Approved {count} expert assignments")


# ========== Invite endpoints (T020) ==========


@router.get("/invites/preview")
async def invite_preview_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    preview = await invite_service.get_invite_preview(session, event.id)
    if not preview:
        raise HTTPException(status_code=404, detail="No approved matching to preview")
    return preview


@router.post("/invites/confirm")
async def invite_confirm_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    result = await invite_service.confirm_invites(session, event.id)
    return result


# ========== Coverage endpoints (EPIC-006: enriched) ==========


@router.get("/coverage")
async def coverage_dashboard_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    dashboard = await coverage_service.get_coverage_summary(session, event.id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="No approved clustering")
    return dashboard


@router.get("/coverage/gaps")
async def coverage_gaps_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    gaps = await coverage_service.get_coverage_gaps(session, event.id)
    if not gaps:
        raise HTTPException(status_code=404, detail="No approved clustering")
    return gaps


@router.get("/coverage/{room_id}")
async def coverage_room_detail_endpoint(
    room_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    detail = await coverage_service.get_room_detail(session, event.id, room_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Room coverage data not found")
    return detail


# ========== Escalation endpoints (T030) ==========


@router.get("/escalations")
async def list_escalations_endpoint(
    resolved: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.services import user_service
    event = await user_service.get_current_event(session)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")

    return await invite_service.get_escalations(session, event.id, resolved=resolved)


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation_endpoint(
    escalation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_organizer(current_user)

    await invite_service.resolve_escalation(session, escalation_id)
    return {"status": "resolved"}
