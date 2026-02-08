"""Admin API endpoints."""

import csv
import io
import json
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models import User
from app.models.role import RoleCode
from app.models.user import GuestSubtype
from app.models.user_role import UserRole
from app.schemas.admin import (
    Alert,
    AuditLogItem,
    AuditLogResponse,
    BriefingPreview,
    BriefingSendResult,
    DashboardResponse,
    EventUpdateRequest,
    ExpertStats,
    GuestDetailResponse,
    GuestListItem,
    GuestStats,
    GuestUploadResult,
    MessagingPreviewRequest,
    MessagingPreviewResponse,
    MessagingSendRequest,
    MessagingSendResult,
    OrganizerCreateRequest,
    OrganizerItem,
    ProjectListItem,
    RoomCoverage,
    RoomDetailResponse,
    RoomStats,
    RoomUpdateRequest,
    RoomUpdateResponse,
    StudentStats,
    TagListResponse,
    TagReplaceRequest,
    TagReplaceResponse,
    TagSuggestResponse,
    TagUpsertRequest,
    TagUpsertResponse,
)
from app.schemas.expert import RowError
from app.schemas.user import EventResponse
from app.services import (
    admin_service,
    audit_service,
    briefing_service,
    dedup_service,
    messaging_service,
    organizer_service,
    user_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics for organizer."""

    event = await user_service.get_current_event(db)
    if not event:
        return DashboardResponse(
            students=StudentStats(total=0, confirmed=0, pending=0, declined=0),
            experts=ExpertStats(total=0, confirmed=0, pending=0, invited=0),
            guests=GuestStats(total=0, by_subtype=[]),
            rooms=RoomStats(total=0, with_experts=0, without_experts=0),
            alerts=[Alert(severity="info", message="Нет активного мероприятия. Загрузите проекты для начала работы.")],
        )

    return await admin_service.get_dashboard_stats(db, event.id)


@router.get("/coverage", response_model=list[RoomCoverage])
async def get_coverage(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get room coverage statistics."""

    event = await user_service.get_current_event(db)
    if not event:
        return []

    return await admin_service.get_coverage_stats(db, event.id)


@router.get("/rooms/{room_id}", response_model=RoomDetailResponse)
async def get_room_detail(
    room_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific room."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    try:
        return await admin_service.get_room_detail(db, event.id, room_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/rooms/{room_id}", response_model=RoomUpdateResponse)
async def update_room(
    room_id: UUID,
    request: RoomUpdateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update room name/theme (organizer-managed)."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    if request.name is None and request.theme_rationale is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nothing to update",
        )

    try:
        room = await admin_service.update_room_theme(
            db,
            event.id,
            room_id,
            name=request.name,
            theme_rationale=request.theme_rationale,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    await audit_service.log_action(
        db, current_user, "room_update",
        entity_type="room", entity_id=str(room.id),
        details={
            "name": room.name,
            "theme_rationale": room.theme_rationale,
        },
    )

    return RoomUpdateResponse(
        id=str(room.id),
        name=room.name,
        theme_rationale=room.theme_rationale,
    )


@router.get("/tags", response_model=TagListResponse)
async def list_tags(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List available tags."""
    tags = await admin_service.list_tags(db)
    return TagListResponse(tags=tags)


@router.post("/tags", response_model=TagUpsertResponse)
async def add_tags(
    request: TagUpsertRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Add optional base tags for conference."""
    added, skipped = await admin_service.add_tags(db, request.tags)

    await audit_service.log_action(
        db, current_user, "tags_add",
        entity_type="tags",
        details={"added": added, "skipped": skipped},
    )

    return TagUpsertResponse(added=added, skipped=skipped)


@router.delete("/tags/{tag_name}", status_code=204)
async def delete_tag(
    tag_name: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a single tag and its project associations."""
    deleted = await admin_service.delete_tag(db, tag_name)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    await audit_service.log_action(
        db, current_user, "tags_delete",
        entity_type="tags",
        details={"deleted": tag_name},
    )


@router.post("/tags/suggest", response_model=TagSuggestResponse)
async def suggest_tags(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Suggest tags based on project descriptions using LLM."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    result = await admin_service.suggest_tags(db, event.id)
    return TagSuggestResponse(**result)


@router.put("/tags", response_model=TagReplaceResponse)
async def replace_tags(
    request: TagReplaceRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Replace all tags with a new set."""
    result = await admin_service.replace_tags(db, request.tags)

    await audit_service.log_action(
        db, current_user, "tags_replace",
        entity_type="tags",
        details={"added": result["added"], "removed": result["removed"]},
    )

    return TagReplaceResponse(**result)


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    return await admin_service.get_projects_list(db, event.id, room_id, status, search)


@router.patch("/events/current", response_model=EventResponse)
async def update_current_event(
    request: EventUpdateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update current event details (name, dates, description)."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    # Determine effective dates for validation
    new_start = request.start_date if request.start_date is not None else event.start_date
    new_end = request.end_date if request.end_date is not None else event.end_date
    if new_end < new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be >= start_date",
        )

    # Apply non-None fields
    changes = {}
    for field in ("name", "start_date", "end_date", "description"):
        value = getattr(request, field)
        if value is not None:
            changes[field] = str(value)
            setattr(event, field, value)

    await audit_service.log_action(
        db, current_user, "event_update",
        entity_type="event", entity_id=str(event.id),
        details=changes,
    )

    await db.commit()
    await db.refresh(event)
    return event


@router.get("/guests", response_model=list[GuestListItem])
async def list_guests(
    search: str | None = None,
    subtype: str | None = None,
    role: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all guests and business partners with profile summaries."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    return await admin_service.list_guests(db, event.id, search, subtype, role)


@router.get("/guests/{user_id}", response_model=GuestDetailResponse)
async def get_guest_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed guest profile."""
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    try:
        return await admin_service.get_guest_detail(db, event.id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/admin/guests/upload", response_model=GuestUploadResult)
async def upload_guests(
    file: UploadFile = File(...),
    default_subtype: str = Query(...),
    confirm_replace: bool = Query(False),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Bulk import guests from CSV or JSON file."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    # Validate subtype
    try:
        subtype_enum = GuestSubtype(default_subtype)
    except ValueError:
        valid = [s.value for s in GuestSubtype]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid subtype '{default_subtype}'. Valid: {valid}",
        )

    # Get guest role
    guest_role = await user_service.get_role_by_code(db, RoleCode.GUEST)
    if not guest_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Guest role not found in database",
        )

    # Check existing guest users for this event
    existing_count = await db.scalar(
        select(func.count(UserRole.id)).where(
            UserRole.event_id == event.id,
            UserRole.role_id == guest_role.id,
        )
    )

    if existing_count and existing_count > 0 and not confirm_replace:
        return GuestUploadResult(
            total_parsed=0,
            imported=0,
            duplicates=0,
            errors=[],
        ).model_dump() | {
            "existing_count": existing_count,
            "message": f"{existing_count} guests already exist. Set confirm_replace=true to replace.",
        }

    if existing_count and existing_count > 0 and confirm_replace:
        # Delete existing guest user_roles and their users for this event
        guest_user_roles = (
            await db.execute(
                select(UserRole).where(
                    UserRole.event_id == event.id,
                    UserRole.role_id == guest_role.id,
                )
            )
        ).scalars().all()
        guest_user_ids = [ur.user_id for ur in guest_user_roles]
        for ur in guest_user_roles:
            await db.delete(ur)
        # Delete users that were created for import (synthetic telegram_user_id)
        for uid in guest_user_ids:
            user = await db.get(User, uid)
            if user and user.telegram_user_id.startswith("guest-"):
                await db.delete(user)
        await db.flush()

    # Parse file
    content = await file.read()
    file_hash = dedup_service.compute_file_hash(content)
    dup_info = await dedup_service.check_recent_duplicate(db, file_hash, "upload_guests")
    filename = file.filename or ""
    rows: list[dict] = []

    if filename.endswith(".json"):
        try:
            data = json.loads(content.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        if not isinstance(data, list):
            raise HTTPException(status_code=400, detail="Expected JSON array")
        rows = data
    elif filename.endswith(".csv"):
        try:
            text = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid CSV file")
    elif filename.endswith(".xlsx"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
            headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(next(rows_iter))]
            for row_values in rows_iter:
                if all(v is None for v in row_values):
                    continue
                rows.append({headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(row_values)})
            wb.close()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid XLSX file")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use .csv, .json or .xlsx")

    # Process rows
    imported = 0
    duplicates = 0
    errors: list[RowError] = []
    seen_names: set[str] = set()

    for i, row in enumerate(rows):
        name = (row.get("name") or "").strip()
        if not name:
            errors.append(RowError(row=i + 1, field="name", message="Name is required"))
            continue

        # Check duplicate within file
        name_lower = name.lower()
        if name_lower in seen_names:
            duplicates += 1
            continue
        seen_names.add(name_lower)

        telegram = (row.get("telegram") or "").strip()
        username = telegram.lstrip("@") if telegram else None

        # Generate synthetic telegram_user_id
        synthetic_id = f"guest-{uuid4().hex[:8]}"

        user = await user_service.upsert_user(
            db,
            telegram_user_id=synthetic_id,
            full_name=name,
            username=username,
        )

        await user_service.set_role(
            db,
            user_id=user.id,
            event_id=event.id,
            role=guest_role,
            guest_subtype=subtype_enum,
        )

        imported += 1

    await audit_service.log_action(
        db, current_user, "upload_guests",
        entity_type="guests",
        details={"imported": imported, "duplicates": duplicates, "errors": len(errors), "file_hash": file_hash},
    )

    return GuestUploadResult(
        total_parsed=len(rows),
        imported=imported,
        duplicates=duplicates,
        errors=errors,
        duplicate_warning=dup_info["warning"] if dup_info else None,
    )


@router.get("/briefing/preview", response_model=BriefingPreview)
async def get_briefing_preview(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get briefing preview: how many experts will receive briefings."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    result = await briefing_service.get_briefing_preview(db, event.id)
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=result["error"]
        )

    return BriefingPreview(**result)


@router.post("/briefing/send", response_model=BriefingSendResult)
async def send_briefings(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Send briefings to all confirmed experts."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    from telegram import Bot

    bot = Bot(token=settings.bot_token)
    result = await briefing_service.send_all_briefings(db, event.id, bot)

    await audit_service.log_action(
        db, current_user, "send_briefing",
        entity_type="briefing",
        details={"sent": result["sent"], "failed": result["failed"], "skipped": result["skipped"]},
    )
    await db.commit()

    return BriefingSendResult(**result)


VALID_MESSAGING_ROLES = {"student", "expert", "guest", "business"}


@router.post("/messaging/preview", response_model=MessagingPreviewResponse)
async def messaging_preview(
    request: MessagingPreviewRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Preview messaging recipients before sending."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    if not request.roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one role must be selected",
        )

    invalid = set(request.roles) - VALID_MESSAGING_ROLES
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid roles: {invalid}. Valid: {VALID_MESSAGING_ROLES}",
        )

    if not request.template.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Template must not be empty",
        )

    result = await messaging_service.preview(
        db, event.id, request.template, request.roles,
        request.guest_subtype, request.room_id,
    )
    return MessagingPreviewResponse(**result)


@router.post("/messaging/send", response_model=MessagingSendResult)
async def messaging_send(
    request: MessagingSendRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Send messages to selected audience."""


    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    if not request.roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one role must be selected",
        )

    invalid = set(request.roles) - VALID_MESSAGING_ROLES
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid roles: {invalid}. Valid: {VALID_MESSAGING_ROLES}",
        )

    if not request.template.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Template must not be empty",
        )

    from telegram import Bot

    bot = Bot(token=settings.bot_token)
    result = await messaging_service.send_messages(
        db, event.id, request.template, request.roles, bot,
        request.guest_subtype, request.room_id,
    )

    await audit_service.log_action(
        db, current_user, "send_messaging",
        entity_type="messaging",
        details={"roles": request.roles, "sent": result["sent"], "failed": result["failed"]},
    )
    await db.commit()

    return MessagingSendResult(**result)


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    action: str | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get paginated admin audit log."""


    entries, total = await audit_service.get_audit_log(db, action=action, limit=limit, offset=offset)

    return AuditLogResponse(
        total=total,
        items=[
            AuditLogItem(
                id=str(e.id),
                created_at=e.created_at,
                user_name=e.user_name,
                action=e.action,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                details=e.details,
            )
            for e in entries
        ],
    )


# ========== Organizer CRUD ==========


@router.get("/organizers", response_model=list[OrganizerItem])
async def list_organizers(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all organizers."""
    organizers = await organizer_service.list_organizers(db)
    return [
        OrganizerItem(
            id=str(o.id),
            telegram_id=o.telegram_id,
            telegram_username=o.telegram_username,
            name=o.name,
            added_by=o.added_by,
            created_at=o.created_at,
        )
        for o in organizers
    ]


@router.post("/organizers", response_model=OrganizerItem, status_code=201)
async def add_organizer(
    request: OrganizerCreateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Add a new organizer."""
    organizer = await organizer_service.add_organizer(
        db,
        telegram_id=request.telegram_id,
        telegram_username=request.telegram_username,
        name=request.name,
        added_by=current_user.full_name,
    )
    await db.commit()
    return OrganizerItem(
        id=str(organizer.id),
        telegram_id=organizer.telegram_id,
        telegram_username=organizer.telegram_username,
        name=organizer.name,
        added_by=organizer.added_by,
        created_at=organizer.created_at,
    )


@router.delete("/organizers/{organizer_id}", status_code=204)
async def delete_organizer(
    organizer_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Remove an organizer."""
    deleted = await organizer_service.remove_organizer(db, organizer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Organizer not found")
    await db.commit()
