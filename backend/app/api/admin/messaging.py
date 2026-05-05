"""Admin messaging endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas.admin import (
    MessagingPreviewRequest,
    MessagingPreviewResponse,
    MessagingSendRequest,
    MessagingSendResult,
)
from app.services.admin import audit_service, messaging_service
from app.services.core import user_service

router = APIRouter()

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active event")

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
        db,
        event.id,
        request.template,
        request.roles,
        request.guest_subtype,
        request.room_id,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active event")

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

    from app.services.core.bot_messenger import get_send_bot

    bot = get_send_bot()
    result = await messaging_service.send_messages(
        db,
        event.id,
        request.template,
        request.roles,
        bot,
        request.guest_subtype,
        request.room_id,
    )

    await audit_service.log_action(
        db,
        current_user,
        "send_messaging",
        entity_type="messaging",
        details={"roles": request.roles, "sent": result["sent"], "failed": result["failed"]},
    )
    await db.commit()

    return MessagingSendResult(**result)
