"""Admin API endpoints."""

import csv
import io
import json
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models import User
from app.models.role import RoleCode
from app.models.user import GuestSubtype
from app.models.user_role import UserRole
from app.schemas.admin import DashboardResponse, EventUpdateRequest, GuestUploadResult, ProjectListItem, RoomCoverage, RoomDetailResponse
from app.schemas.expert import RowError
from app.schemas.user import EventResponse
from app.services import admin_service, user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


def _check_organizer(user: User) -> None:
    """Check if user is an organizer."""
    if not user.telegram_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not an organizer"
        )
    if user.telegram_user_id not in settings.organizer_telegram_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not an organizer"
        )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics for organizer."""
    _check_organizer(current_user)

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    return await admin_service.get_dashboard_stats(db, event.id)


@router.get("/coverage", response_model=list[RoomCoverage])
async def get_coverage(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get room coverage statistics."""
    _check_organizer(current_user)

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    return await admin_service.get_coverage_stats(db, event.id)


@router.get("/rooms/{room_id}", response_model=RoomDetailResponse)
async def get_room_detail(
    room_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific room."""
    _check_organizer(current_user)

    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active event"
        )

    try:
        return await admin_service.get_room_detail(db, event.id, room_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/projects", response_model=list[ProjectListItem])
async def get_projects(
    room_id: UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get list of all projects with optional filters."""
    _check_organizer(current_user)

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
    _check_organizer(current_user)

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
    for field in ("name", "start_date", "end_date", "description"):
        value = getattr(request, field)
        if value is not None:
            setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return event


@router.post("/admin/guests/upload", response_model=GuestUploadResult)
async def upload_guests(
    file: UploadFile = File(...),
    default_subtype: str = Query(...),
    confirm_replace: bool = Query(False),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Bulk import guests from CSV or JSON file."""
    _check_organizer(current_user)

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
        ).model_dump() | {"existing_count": existing_count, "message": f"{existing_count} guests already exist. Set confirm_replace=true to replace."}

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
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use .csv or .json")

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

    return GuestUploadResult(
        total_parsed=len(rows),
        imported=imported,
        duplicates=duplicates,
        errors=errors,
    )
