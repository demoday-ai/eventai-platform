"""Admin audit log endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas.admin import AuditLogItem, AuditLogResponse
from app.services.admin import audit_service

router = APIRouter()


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
