"""Event & clustering data access."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clustering_run import ClusteringRun
from app.models.event import Event


async def get_current_event(session: AsyncSession) -> Event | None:
    """Get the most recent event."""
    result = await session.execute(select(Event).order_by(Event.start_date.desc()).limit(1))
    return result.scalar_one_or_none()


async def get_approved_clustering(session: AsyncSession, event_id: UUID) -> ClusteringRun | None:
    """Get the latest approved clustering run for an event."""
    result = await session.scalar(
        select(ClusteringRun)
        .where(
            ClusteringRun.event_id == event_id,
            ClusteringRun.status == "approved",
        )
        .order_by(ClusteringRun.created_at.desc())
        .limit(1)
    )
    return result
