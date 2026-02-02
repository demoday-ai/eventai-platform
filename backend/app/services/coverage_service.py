"""Read-only coverage aggregation service for EPIC-006: Organizer Coverage Dashboard.

Provides enriched coverage data: project counts, tag analysis, gap detection,
and expert candidate recommendations. Extends EPIC-004 coverage functions
with project/tag-level intelligence.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expert import Expert
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.expert_tag import ExpertTag
from app.models.project_tag import ProjectTag
from app.models.room import Room
from app.models.room_project import RoomProject
from app.models.tag import Tag
from app.services import matching_service

logger = logging.getLogger(__name__)

# Pending statuses for coverage counting
_PENDING_STATUSES = frozenset({"proposed", "approved", "invite_ready", "invited"})


async def get_coverage_summary(session: AsyncSession, event_id) -> dict | None:
    """Per-room coverage summary with project counts, top tags, expert counts.

    Returns dict matching CoverageSummary schema or None if no approved clustering.
    """
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return None

    rooms_result = await session.execute(
        select(Room)
        .where(Room.clustering_run_id == clustering.id)
        .order_by(Room.display_order)
    )
    rooms = rooms_result.scalars().all()
    if not rooms:
        return None

    rooms_data = []
    total_confirmed = 0
    total_pending = 0
    total_declined = 0
    total_needed = 0

    for room in rooms:
        # Project count
        project_count_result = await session.execute(
            select(func.count(RoomProject.id))
            .where(RoomProject.room_id == room.id)
        )
        project_count = project_count_result.scalar() or 0

        # Top 5 project tags by frequency
        top_tags_result = await session.execute(
            select(Tag.name, func.count(ProjectTag.id).label("cnt"))
            .join(ProjectTag, ProjectTag.tag_id == Tag.id)
            .join(RoomProject, RoomProject.project_id == ProjectTag.project_id)
            .where(RoomProject.room_id == room.id)
            .group_by(Tag.name)
            .order_by(func.count(ProjectTag.id).desc())
            .limit(5)
        )
        top_tags = [row[0] for row in top_tags_result.all()]

        # Expert counts by status
        asgn_result = await session.execute(
            select(ExpertRoomAssignment)
            .where(ExpertRoomAssignment.room_id == room.id)
            .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        )
        room_assignments = asgn_result.scalars().all()

        confirmed = sum(1 for a in room_assignments if a.status == "confirmed")
        pending = sum(1 for a in room_assignments if a.status in _PENDING_STATUSES)
        declined = sum(1 for a in room_assignments if a.status == "declined")

        if confirmed >= 2:
            coverage_level = "covered"
        elif confirmed >= 1:
            coverage_level = "partial"
        else:
            coverage_level = "uncovered"

        rooms_data.append({
            "room_id": str(room.id),
            "room_name": room.name,
            "project_count": project_count,
            "top_tags": top_tags,
            "confirmed": confirmed,
            "pending": pending,
            "declined": declined,
            "total_assigned": len(room_assignments),
            "coverage_level": coverage_level,
        })

        total_confirmed += confirmed
        total_pending += pending
        total_declined += declined
        total_needed += 2  # minimum 2 experts per room

    coverage_percent = (total_confirmed / total_needed * 100) if total_needed > 0 else 0

    return {
        "rooms": rooms_data,
        "totals": {
            "confirmed": total_confirmed,
            "pending": total_pending,
            "declined": total_declined,
            "total_needed": total_needed,
            "coverage_percent": round(coverage_percent, 1),
        },
    }


async def get_room_detail(session: AsyncSession, event_id, room_id) -> dict | None:
    """Room detail: experts, project tags, uncovered tags, candidate experts.

    Returns dict matching RoomCoverageDetail schema or None.
    """
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return None

    # Verify room exists in this clustering
    room_result = await session.execute(
        select(Room)
        .where(Room.id == room_id)
        .where(Room.clustering_run_id == clustering.id)
    )
    room = room_result.scalars().first()
    if not room:
        return None

    # Project count
    project_count_result = await session.execute(
        select(func.count(RoomProject.id))
        .where(RoomProject.room_id == room_id)
    )
    project_count = project_count_result.scalar() or 0

    # All distinct project tags in room
    project_tags_result = await session.execute(
        select(Tag.name)
        .join(ProjectTag, ProjectTag.tag_id == Tag.id)
        .join(RoomProject, RoomProject.project_id == ProjectTag.project_id)
        .where(RoomProject.room_id == room_id)
        .distinct()
    )
    project_tags = sorted([row[0] for row in project_tags_result.all()])

    # Experts assigned to this room
    asgn_result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.room_id == room_id)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .options(
            selectinload(ExpertRoomAssignment.expert)
            .selectinload(Expert.tags)
            .selectinload(ExpertTag.tag),
        )
    )
    assignments = asgn_result.scalars().all()

    experts = []
    confirmed_expert_tags = set()
    for a in assignments:
        expert_tag_names = [et.tag.name for et in a.expert.tags]
        experts.append({
            "expert_id": str(a.expert.id),
            "name": a.expert.name,
            "status": a.status,
            "match_score": a.match_score,
            "tags": expert_tag_names,
            "bot_started": a.expert.bot_started,
        })
        if a.status == "confirmed":
            confirmed_expert_tags.update(expert_tag_names)

    # Uncovered tags = project tags minus confirmed expert tags
    uncovered_tags = sorted(set(project_tags) - confirmed_expert_tags)

    # Find candidates for uncovered tags
    candidates = []
    if uncovered_tags:
        candidates = await _find_candidates_for_tags(
            session, uncovered_tags, room_id, clustering.id
        )

    return {
        "room_id": str(room_id),
        "room_name": room.name,
        "project_count": project_count,
        "project_tags": project_tags,
        "experts": experts,
        "uncovered_tags": uncovered_tags,
        "candidates": candidates,
    }


async def find_expert_candidates(
    session: AsyncSession, tag_name: str, exclude_room_id, clustering_run_id
) -> list[dict]:
    """Find experts with matching tag not assigned to target room.

    Returns list of dicts matching ExpertCandidate schema.
    """
    # Experts who have this tag
    experts_with_tag = await session.execute(
        select(Expert)
        .join(ExpertTag, ExpertTag.expert_id == Expert.id)
        .join(Tag, Tag.id == ExpertTag.tag_id)
        .where(Tag.name == tag_name)
        .options(
            selectinload(Expert.tags).selectinload(ExpertTag.tag),
            selectinload(Expert.assignments).selectinload(ExpertRoomAssignment.room),
        )
    )
    experts = experts_with_tag.scalars().unique().all()

    candidates = []
    for expert in experts:
        # Check if already assigned to the target room in this clustering
        assigned_to_target = any(
            a.room_id == exclude_room_id and a.clustering_run_id == clustering_run_id
            for a in expert.assignments
        )
        if assigned_to_target:
            continue

        current_rooms = [
            a.room.name
            for a in expert.assignments
            if a.clustering_run_id == clustering_run_id and a.room
        ]
        matching_tags = [et.tag.name for et in expert.tags]

        candidates.append({
            "expert_id": str(expert.id),
            "name": expert.name,
            "matching_tags": matching_tags,
            "current_rooms": current_rooms,
        })

    return candidates


async def get_coverage_gaps(session: AsyncSession, event_id) -> dict | None:
    """All uncovered tags across all rooms with candidate experts.

    Returns dict matching CoverageGapsList schema or None.
    """
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return None

    rooms_result = await session.execute(
        select(Room)
        .where(Room.clustering_run_id == clustering.id)
        .order_by(Room.display_order)
    )
    rooms = rooms_result.scalars().all()

    gaps = []
    for room in rooms:
        # Project tags in this room with counts
        tag_counts_result = await session.execute(
            select(Tag.name, func.count(ProjectTag.id).label("cnt"))
            .join(ProjectTag, ProjectTag.tag_id == Tag.id)
            .join(RoomProject, RoomProject.project_id == ProjectTag.project_id)
            .where(RoomProject.room_id == room.id)
            .group_by(Tag.name)
        )
        tag_counts = {row[0]: row[1] for row in tag_counts_result.all()}

        if not tag_counts:
            continue

        # Confirmed expert tags in this room
        confirmed_asgn = await session.execute(
            select(ExpertRoomAssignment)
            .where(ExpertRoomAssignment.room_id == room.id)
            .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
            .where(ExpertRoomAssignment.status == "confirmed")
            .options(
                selectinload(ExpertRoomAssignment.expert)
                .selectinload(Expert.tags)
                .selectinload(ExpertTag.tag),
            )
        )
        confirmed_assignments = confirmed_asgn.scalars().all()

        confirmed_expert_tags = set()
        for a in confirmed_assignments:
            for et in a.expert.tags:
                confirmed_expert_tags.add(et.tag.name)

        # Uncovered tags
        uncovered = set(tag_counts.keys()) - confirmed_expert_tags

        for tag_name in sorted(uncovered):
            candidates = await find_expert_candidates(
                session, tag_name, room.id, clustering.id
            )
            gaps.append({
                "room_id": str(room.id),
                "room_name": room.name,
                "uncovered_tag": tag_name,
                "project_count_with_tag": tag_counts[tag_name],
                "candidates": candidates,
            })

    return {
        "total_gaps": len(gaps),
        "gaps": gaps,
    }


async def _find_candidates_for_tags(
    session: AsyncSession,
    uncovered_tags: list[str],
    exclude_room_id,
    clustering_run_id,
) -> list[dict]:
    """Find unique candidate experts across multiple uncovered tags."""
    seen_expert_ids = set()
    candidates = []

    for tag_name in uncovered_tags:
        tag_candidates = await find_expert_candidates(
            session, tag_name, exclude_room_id, clustering_run_id
        )
        for c in tag_candidates:
            if c["expert_id"] not in seen_expert_ids:
                seen_expert_ids.add(c["expert_id"])
                candidates.append(c)

    return candidates
