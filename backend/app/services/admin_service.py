"""Admin dashboard service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ExpertRoomAssignment,
    ParticipationRequest,
    ParticipationStatus,
    Project,
    Role,
    RoleCode,
    Room,
    ScheduleSlot,
    User,
    UserRole,
)
from app.schemas.admin import (
    Alert,
    CoverageResponse,
    DashboardResponse,
    ExpertStats,
    GuestStats,
    GuestSubtypeCount,
    RoomCoverage,
    RoomStats,
    StudentStats,
)


async def get_dashboard_stats(db: AsyncSession, event_id: UUID) -> DashboardResponse:
    """Get dashboard statistics for organizer."""

    # Students stats
    total_students = await db.scalar(
        select(func.count(Project.id)).where(Project.event_id == event_id)
    )

    confirmed_students = await db.scalar(
        select(func.count(ParticipationRequest.id)).where(
            ParticipationRequest.event_id == event_id,
            ParticipationRequest.status == ParticipationStatus.ACKNOWLEDGED,
        )
    )

    pending_students = await db.scalar(
        select(func.count(ParticipationRequest.id)).where(
            ParticipationRequest.event_id == event_id,
            ParticipationRequest.status.in_([ParticipationStatus.PENDING, ParticipationStatus.SENT]),
        )
    )

    # Declined = total - confirmed - pending
    declined_students = total_students - confirmed_students - pending_students

    students = StudentStats(
        total=total_students,
        confirmed=confirmed_students,
        pending=pending_students,
        declined=max(0, declined_students),
    )

    # Expert stats
    # Get current clustering run
    from app.models import ClusteringRun

    current_clustering = await db.scalar(
        select(ClusteringRun)
        .where(ClusteringRun.event_id == event_id, ClusteringRun.status == "approved")
        .order_by(ClusteringRun.created_at.desc())
        .limit(1)
    )

    if current_clustering:
        total_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.expert_id.distinct())).where(
                ExpertRoomAssignment.clustering_run_id == current_clustering.id
            )
        )

        confirmed_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.expert_id.distinct())).where(
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
                ExpertRoomAssignment.status == "confirmed",
            )
        )

        pending_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.expert_id.distinct())).where(
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
                ExpertRoomAssignment.status.in_(["proposed", "sent"]),
            )
        )

        invited_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.expert_id.distinct())).where(
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
                ExpertRoomAssignment.status.in_(["sent", "confirmed"]),
            )
        )
    else:
        total_experts = confirmed_experts = pending_experts = invited_experts = 0

    experts = ExpertStats(
        total=total_experts,
        confirmed=confirmed_experts,
        pending=pending_experts,
        invited=invited_experts,
    )

    # Guest stats
    guest_role = await db.scalar(select(Role).where(Role.code == RoleCode.GUEST.value))

    total_guests = 0
    by_subtype = []

    if guest_role:
        total_guests = await db.scalar(
            select(func.count(UserRole.user_id.distinct())).where(
                UserRole.event_id == event_id, UserRole.role_id == guest_role.id
            )
        )

        # Get guest subtypes
        subtype_result = await db.execute(
            select(User.guest_subtype, func.count(User.id))
            .select_from(UserRole)
            .join(User, UserRole.user_id == User.id)
            .where(
                UserRole.event_id == event_id,
                UserRole.role_id == guest_role.id,
                User.guest_subtype.isnot(None),
            )
            .group_by(User.guest_subtype)
        )

        by_subtype = [
            GuestSubtypeCount(subtype=row[0], count=row[1]) for row in subtype_result.all()
        ]

    guests = GuestStats(total=total_guests, by_subtype=by_subtype)

    # Room stats
    total_rooms = await db.scalar(
        select(func.count(Room.id)).where(Room.event_id == event_id)
    )

    if current_clustering:
        rooms_with_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.room_id.distinct())).where(
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
                ExpertRoomAssignment.status == "confirmed",
            )
        )
    else:
        rooms_with_experts = 0

    rooms = RoomStats(
        total=total_rooms,
        with_experts=rooms_with_experts,
        without_experts=total_rooms - rooms_with_experts,
    )

    # Alerts
    alerts = []

    # Rooms without experts
    if current_clustering and rooms.without_experts > 0:
        # Get room names without experts
        rooms_result = await db.execute(
            select(Room.id, Room.name)
            .where(Room.event_id == event_id)
            .where(
                ~Room.id.in_(
                    select(ExpertRoomAssignment.room_id.distinct()).where(
                        ExpertRoomAssignment.clustering_run_id == current_clustering.id,
                        ExpertRoomAssignment.status == "confirmed",
                    )
                )
            )
        )

        for room_id, room_name in rooms_result.all():
            alerts.append(
                Alert(
                    severity="critical",
                    message=f"Зал без экспертов",
                    room_id=str(room_id),
                    room_name=room_name,
                )
            )

    # Empty slots (if schedule exists)
    empty_slots = await db.scalar(
        select(func.count(ScheduleSlot.id)).where(
            ScheduleSlot.event_id == event_id, ScheduleSlot.project_id.is_(None)
        )
    )

    if empty_slots > 0:
        alerts.append(
            Alert(
                severity="warning",
                message=f"Пустых слотов: {empty_slots}",
            )
        )

    # Pending students close to DD
    if pending_students > 10:
        alerts.append(
            Alert(
                severity="warning",
                message=f"Не подтвердили участие: {pending_students} студентов",
            )
        )

    return DashboardResponse(
        students=students, experts=experts, guests=guests, rooms=rooms, alerts=alerts
    )


async def get_coverage_stats(db: AsyncSession, event_id: UUID) -> list[RoomCoverage]:
    """Get room coverage statistics."""
    # Get current clustering run
    from app.models import ClusteringRun

    current_clustering = await db.scalar(
        select(ClusteringRun)
        .where(ClusteringRun.event_id == event_id, ClusteringRun.status == "approved")
        .order_by(ClusteringRun.created_at.desc())
        .limit(1)
    )

    if not current_clustering:
        return []

    # Get all rooms for this event
    rooms_result = await db.execute(select(Room).where(Room.event_id == event_id))
    rooms = rooms_result.scalars().all()

    coverage_list = []

    for room in rooms:
        # Count projects in this room
        from app.models import RoomProject

        projects_count = await db.scalar(
            select(func.count(RoomProject.id)).where(
                RoomProject.room_id == room.id,
                RoomProject.clustering_run_id == current_clustering.id,
            )
        )

        # Count total experts assigned to this room
        total_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.id)).where(
                ExpertRoomAssignment.room_id == room.id,
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
            )
        )

        # Count confirmed experts
        confirmed_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.id)).where(
                ExpertRoomAssignment.room_id == room.id,
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
                ExpertRoomAssignment.status == "confirmed",
            )
        )

        # Determine coverage status
        if total_experts == 0:
            coverage_status = "none"
        elif confirmed_experts == total_experts:
            coverage_status = "full"
        else:
            coverage_status = "partial"

        coverage_list.append(
            RoomCoverage(
                room_id=str(room.id),
                room_name=room.name,
                total_experts=total_experts or 0,
                confirmed_experts=confirmed_experts or 0,
                projects_count=projects_count or 0,
                coverage_status=coverage_status,
            )
        )

    return coverage_list
