"""Admin dashboard service."""

import logging
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ClusteringRun,
    Expert,
    ExpertRoomAssignment,
    ParticipationRequest,
    ParticipationStatus,
    Project,
    ProjectTag,
    Role,
    RoleCode,
    Room,
    RoomProject,
    ScheduleSlot,
    Tag,
    User,
    UserRole,
)
from app.schemas.admin import (
    Alert,
    DashboardResponse,
    ExpertInfo,
    ExpertStats,
    GuestStats,
    GuestSubtypeCount,
    ProjectInfo,
    ProjectListItem,
    RoomCoverage,
    RoomDetailResponse,
    RoomInfo,
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

    # Expert stats - count from Expert table
    total_experts = await db.scalar(
        select(func.count(Expert.id)).where(Expert.event_id == event_id)
    ) or 0

    # Get current clustering run for assignment stats
    from app.models import ClusteringRun

    current_clustering = await db.scalar(
        select(ClusteringRun)
        .where(ClusteringRun.event_id == event_id, ClusteringRun.status == "approved")
        .order_by(ClusteringRun.created_at.desc())
        .limit(1)
    )

    if current_clustering:
        confirmed_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.expert_id.distinct())).where(
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
                ExpertRoomAssignment.status == "confirmed",
            )
        ) or 0

        pending_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.expert_id.distinct())).where(
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
                ExpertRoomAssignment.status.in_(["proposed", "sent"]),
            )
        ) or 0

        invited_experts = await db.scalar(
            select(func.count(ExpertRoomAssignment.expert_id.distinct())).where(
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
                ExpertRoomAssignment.status.in_(["sent", "confirmed"]),
            )
        ) or 0
    else:
        confirmed_experts = pending_experts = invited_experts = 0

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
    total_rooms = 0
    if current_clustering:
        total_rooms = await db.scalar(
            select(func.count(Room.id)).where(Room.clustering_run_id == current_clustering.id)
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
            .where(Room.clustering_run_id == current_clustering.id)
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
                    message="Зал без экспертов",
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
    rooms_result = await db.execute(
        select(Room).where(Room.clustering_run_id == current_clustering.id)
    )
    rooms = rooms_result.scalars().all()

    coverage_list = []

    for room in rooms:
        # Count projects in this room
        from app.models import RoomProject

        projects_count = await db.scalar(
            select(func.count(RoomProject.id)).where(RoomProject.room_id == room.id)
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


async def get_room_detail(db: AsyncSession, event_id: UUID, room_id: UUID) -> RoomDetailResponse:
    """Get detailed information about a specific room."""
    # Uses ClusteringRun/ProjectTag/RoomProject/Tag via module imports

    # Get room
    room = await db.scalar(
        select(Room)
        .join(ClusteringRun, Room.clustering_run_id == ClusteringRun.id)
        .where(Room.id == room_id, ClusteringRun.event_id == event_id)
    )
    if not room:
        raise ValueError("Room not found")

    # Get current clustering run
    current_clustering = await db.scalar(
        select(ClusteringRun)
        .where(ClusteringRun.event_id == event_id, ClusteringRun.status == "approved")
        .order_by(ClusteringRun.created_at.desc())
        .limit(1)
    )

    # Get experts assigned to this room
    experts_list = []
    if current_clustering:
        experts_result = await db.execute(
            select(ExpertRoomAssignment, User)
            .join(User, ExpertRoomAssignment.expert_id == User.id)
            .where(
                ExpertRoomAssignment.room_id == room_id,
                ExpertRoomAssignment.clustering_run_id == current_clustering.id,
            )
        )

        for assignment, user in experts_result.all():
            # Get expert tags
            tags_result = await db.execute(
                select(Tag.name)
                .select_from(ExpertRoomAssignment)
                .join(Room, ExpertRoomAssignment.room_id == Room.id)
                .join(ProjectTag, ProjectTag.tag_id == Tag.id)
                .where(ExpertRoomAssignment.id == assignment.id)
                .distinct()
            )
            tags = [tag[0] for tag in tags_result.all()]

            # Map status
            status_map = {
                "proposed": "pending",
                "sent": "pending",
                "confirmed": "confirmed",
                "declined": "declined",
            }

            experts_list.append(
                ExpertInfo(
                    id=str(user.id),
                    name=user.full_name or f"User {user.telegram_user_id}",
                    status=status_map.get(assignment.status, "pending"),
                    tags=tags or [],
                )
            )

    # Get projects in this room
    projects_list = []
    if current_clustering:
        projects_result = await db.execute(
            select(RoomProject, Project, ScheduleSlot)
            .join(Project, RoomProject.project_id == Project.id)
            .outerjoin(
                ScheduleSlot,
                (ScheduleSlot.project_id == Project.id) & (ScheduleSlot.room_id == room_id),
            )
            .where(RoomProject.room_id == room_id)
        )

        for room_project, project, schedule_slot in projects_result.all():
            # Get project status
            status = "pending"
            if schedule_slot:
                status = "confirmed"

            # Default times if no schedule
            start_time = schedule_slot.start_time if schedule_slot else "TBD"
            end_time = schedule_slot.end_time if schedule_slot else "TBD"

            projects_list.append(
                ProjectInfo(
                    id=str(project.id),
                    title=project.title,
                    author=project.author or "Unknown",
                    start_time=start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time),
                    end_time=end_time.isoformat() if hasattr(end_time, "isoformat") else str(end_time),
                    status=status,
                )
            )

    # Get uncovered topics
    # Topics from projects that don't match expert tags
    uncovered_topics = []
    if current_clustering:
        # Get all project tags in this room
        project_tags_result = await db.execute(
            select(Tag.name)
            .select_from(RoomProject)
            .join(ProjectTag, ProjectTag.project_id == RoomProject.project_id)
            .join(Tag, ProjectTag.tag_id == Tag.id)
            .where(RoomProject.room_id == room_id)
            .distinct()
        )
        project_tags = {tag[0] for tag in project_tags_result.all()}

        # Get all expert tags in this room
        expert_tags = {tag for expert in experts_list for tag in expert.tags}

        # Uncovered = project tags not in expert tags
        uncovered_topics = sorted(project_tags - expert_tags)

    return RoomDetailResponse(
        room=RoomInfo(
            id=str(room.id),
            name=room.name,
            description=room.theme_rationale or "",
            theme_rationale=room.theme_rationale,
        ),
        experts=experts_list,
        projects=projects_list,
        uncovered_topics=uncovered_topics,
    )


async def get_projects_list(
    db: AsyncSession,
    event_id: UUID,
    room_id: UUID | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[ProjectListItem]:
    """Get list of projects with filters."""
    from app.models import ClusteringRun, ProjectTag, RoomProject, Tag

    # Get current clustering run
    current_clustering = await db.scalar(
        select(ClusteringRun)
        .where(ClusteringRun.event_id == event_id, ClusteringRun.status == "approved")
        .order_by(ClusteringRun.created_at.desc())
        .limit(1)
    )

    if not current_clustering:
        return []

    # Build query
    query = (
        select(RoomProject, Project, Room, ScheduleSlot)
        .join(Project, RoomProject.project_id == Project.id)
        .join(Room, RoomProject.room_id == Room.id)
        .outerjoin(
            ScheduleSlot,
            (ScheduleSlot.project_id == Project.id) & (ScheduleSlot.room_id == Room.id),
        )
        .where(Room.clustering_run_id == current_clustering.id)
    )

    # Apply filters
    if room_id:
        query = query.where(RoomProject.room_id == room_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Project.title.ilike(search_pattern)) | (Project.author.ilike(search_pattern))
        )

    # Execute query
    result = await db.execute(query.order_by(Room.name, ScheduleSlot.start_time.nulls_last()))
    rows = result.all()

    # Build project list
    projects_list = []
    for room_project, project, room, schedule_slot in rows:
        # Determine status
        project_status = "pending"
        if schedule_slot:
            project_status = "confirmed"

        # Filter by status if provided
        if status and project_status != status:
            continue

        # Get project tags
        tags_result = await db.execute(
            select(Tag.name)
            .select_from(ProjectTag)
            .join(Tag, ProjectTag.tag_id == Tag.id)
            .where(ProjectTag.project_id == project.id)
        )
        tags = [tag[0] for tag in tags_result.all()]

        # Default times if no schedule
        start_time = schedule_slot.start_time if schedule_slot else "TBD"
        end_time = schedule_slot.end_time if schedule_slot else "TBD"

        projects_list.append(
            ProjectListItem(
                id=str(project.id),
                title=project.title,
                author=project.author or "Unknown",
                room_id=str(room.id),
                room_name=room.name,
                start_time=start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time),
                end_time=end_time.isoformat() if hasattr(end_time, "isoformat") else str(end_time),
                status=project_status,
                tags=tags,
            )
        )

    return projects_list


async def list_tags(db: AsyncSession) -> list[str]:
    """List all available tags."""
    result = await db.execute(select(Tag.name).order_by(Tag.name))
    return [row[0] for row in result.all()]


async def add_tags(db: AsyncSession, tags: list[str]) -> tuple[list[str], list[str]]:
    """Add new tags (dedupe by lowercase). Returns (added, skipped)."""
    cleaned = [t.strip() for t in tags if t and t.strip()]
    if not cleaned:
        return [], []

    existing_result = await db.execute(select(Tag.name))
    existing = {row[0].lower() for row in existing_result.all()}

    added: list[str] = []
    skipped: list[str] = []
    for tag in cleaned:
        if tag.lower() in existing:
            skipped.append(tag)
            continue
        db.add(Tag(name=tag))
        existing.add(tag.lower())
        added.append(tag)

    if added:
        await db.commit()

    return added, skipped


async def update_room_theme(
    db: AsyncSession,
    event_id: UUID,
    room_id: UUID,
    name: str | None = None,
    theme_rationale: str | None = None,
) -> Room:
    """Update room name/theme for current event."""
    room = await db.scalar(
        select(Room)
        .join(ClusteringRun, Room.clustering_run_id == ClusteringRun.id)
        .where(Room.id == room_id, ClusteringRun.event_id == event_id)
    )
    if not room:
        raise ValueError("Room not found")

    if name is not None:
        room.name = name.strip() or room.name
    if theme_rationale is not None:
        room.theme_rationale = theme_rationale.strip() or room.theme_rationale

    await db.commit()
    await db.refresh(room)
    return room


logger = logging.getLogger(__name__)

TAG_SUGGEST_SYSTEM = (
    "Ты AI-ассистент для организатора Demo Day. "
    "Проанализируй названия и описания проектов и предложи 10-20 тегов "
    "для классификации этих проектов по тематикам. "
    "Теги должны быть короткие (1-2 слова), на английском языке. "
    "Верни JSON строго в формате:\n"
    '{"tags": ["EdTech", "NLP", "CV", ...]}'
)


async def suggest_tags(db: AsyncSession, event_id: UUID) -> dict:
    """Analyze project descriptions and suggest tags via LLM."""
    from app.services import llm_client

    result = await db.execute(
        select(Project.title, Project.description)
        .where(Project.event_id == event_id)
        .limit(50)
    )
    projects = result.all()

    if not projects:
        return {"suggested_tags": [], "project_count": 0}

    summaries = []
    for title, description in projects:
        desc_short = (description or "")[:200]
        summaries.append(f"- {title}: {desc_short}")

    user_prompt = "Проекты:\n" + "\n".join(summaries)

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=TAG_SUGGEST_SYSTEM,
            user_prompt=user_prompt,
            json_mode=True,
        )
        suggested = response.get("tags", [])
        # Ensure all tags are strings
        suggested = [str(t).strip() for t in suggested if t and str(t).strip()]
        return {"suggested_tags": suggested, "project_count": len(projects)}
    except Exception:
        logger.exception("LLM tag suggestion failed")
        return {"suggested_tags": [], "project_count": len(projects)}


async def replace_tags(db: AsyncSession, tags: list[str]) -> dict:
    """Replace all tags with a new set. Returns added/removed/final lists."""
    cleaned = list(dict.fromkeys(t.strip() for t in tags if t and t.strip()))

    # Get existing tags
    existing_result = await db.execute(select(Tag.id, Tag.name))
    existing_map = {row[1]: row[0] for row in existing_result.all()}
    existing_names = set(existing_map.keys())
    new_names = set(cleaned)

    to_add = new_names - existing_names
    to_remove = existing_names - new_names

    added = []
    for name in sorted(to_add):
        db.add(Tag(name=name))
        added.append(name)

    removed = []
    for name in sorted(to_remove):
        tag_id = existing_map[name]
        # Check if tag is used by any project
        usage_count = await db.scalar(
            select(func.count(ProjectTag.id)).where(ProjectTag.tag_id == tag_id)
        )
        if usage_count and usage_count > 0:
            # Tag is in use — keep it but note it
            continue
        await db.execute(delete(Tag).where(Tag.id == tag_id))
        removed.append(name)

    await db.commit()

    # Return final state
    final_result = await db.execute(select(Tag.name).order_by(Tag.name))
    final_tags = [row[0] for row in final_result.all()]

    return {"final_tags": final_tags, "added": added, "removed": removed}
