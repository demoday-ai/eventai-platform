"""Admin tour status endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.models.tour_status import AdminTourStatus

router = APIRouter(prefix="/tour", tags=["admin-tour"])


@router.get("/status")
async def get_tour_status(
    db: AsyncSession = Depends(get_db),
    telegram_id: str = Depends(get_current_user_id),
):
    """Get tour completion status for current user."""
    status = await db.get(AdminTourStatus, telegram_id)

    if not status:
        return {
            "prompted": False,
            "completed": False,
            "prompted_at": None,
            "completed_at": None,
        }

    return {
        "prompted": status.prompted_at is not None,
        "completed": status.completed_at is not None,
        "prompted_at": status.prompted_at.isoformat() if status.prompted_at else None,
        "completed_at": status.completed_at.isoformat() if status.completed_at else None,
    }


@router.post("/mark-prompted")
async def mark_tour_prompted(
    db: AsyncSession = Depends(get_db),
    telegram_id: str = Depends(get_current_user_id),
):
    """Mark tour as prompted (user saw the welcome dialog)."""
    status = await db.get(AdminTourStatus, telegram_id)

    if not status:
        status = AdminTourStatus(
            telegram_id=telegram_id,
            prompted_at=datetime.now(timezone.utc),
        )
        db.add(status)
    else:
        if not status.prompted_at:
            status.prompted_at = datetime.now(timezone.utc)

    await db.commit()
    return {"success": True}


@router.post("/mark-completed")
async def mark_tour_completed(
    db: AsyncSession = Depends(get_db),
    telegram_id: str = Depends(get_current_user_id),
):
    """Mark tour as completed."""
    status = await db.get(AdminTourStatus, telegram_id)

    if not status:
        status = AdminTourStatus(
            telegram_id=telegram_id,
            prompted_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(status)
    else:
        status.completed_at = datetime.now(timezone.utc)
        if not status.prompted_at:
            status.prompted_at = datetime.now(timezone.utc)

    await db.commit()
    return {"success": True}


@router.post("/reset")
async def reset_tour_status(
    db: AsyncSession = Depends(get_db),
    telegram_id: str = Depends(get_current_user_id),
):
    """Reset tour status (for 'restart tour' button)."""
    status = await db.get(AdminTourStatus, telegram_id)

    if status:
        await db.delete(status)
        await db.commit()

    return {"success": True}
