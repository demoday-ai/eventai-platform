"""Room data access."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clustering_run import ClusteringRun
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.room import Room
from app.models.room_project import RoomProject


async def get_by_id(session: AsyncSession, room_id: UUID) -> Room | None:
    return await session.get(Room, room_id)


async def get_by_event(session: AsyncSession, room_id: UUID, event_id: UUID) -> Room | None:
    """Get room that belongs to a clustering run of the given event."""
    return await session.scalar(
        select(Room)
        .join(ClusteringRun, Room.clustering_run_id == ClusteringRun.id)
        .where(Room.id == room_id, ClusteringRun.event_id == event_id)
    )


async def get_rooms_by_clustering(session: AsyncSession, clustering_run_id: UUID) -> list[Room]:
    result = await session.execute(select(Room).where(Room.clustering_run_id == clustering_run_id))
    return list(result.scalars().all())


async def count_rooms(session: AsyncSession, clustering_run_id: UUID) -> int:
    return await session.scalar(select(func.count(Room.id)).where(Room.clustering_run_id == clustering_run_id)) or 0


async def count_projects_in_room(session: AsyncSession, room_id: UUID) -> int:
    return await session.scalar(select(func.count(RoomProject.id)).where(RoomProject.room_id == room_id)) or 0


async def count_experts_in_room(
    session: AsyncSession, room_id: UUID, clustering_run_id: UUID, status: str | None = None
) -> int:
    query = select(func.count(ExpertRoomAssignment.id)).where(
        ExpertRoomAssignment.room_id == room_id,
        ExpertRoomAssignment.clustering_run_id == clustering_run_id,
    )
    if status:
        query = query.where(ExpertRoomAssignment.status == status)
    return await session.scalar(query) or 0
