"""Admin guest management endpoints."""

import csv
import io
import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.models.role import RoleCode
from app.models.user import GuestSubtype
from app.models.user_role import UserRole
from app.schemas.admin import (
    GuestDetailResponse,
    GuestListItem,
    GuestUploadResult,
)
from app.schemas.expert import RowError
from app.services.admin import admin_service, audit_service, dedup_service
from app.services.core import user_service

router = APIRouter()


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
