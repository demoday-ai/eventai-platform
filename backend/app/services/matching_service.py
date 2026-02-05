"""Expert-room matching service: IDF-weighted tag overlap with LLM adjacent tags."""

import json
import logging
import math
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clustering_run import ClusteringRun
from app.models.expert import Expert
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.expert_tag import ExpertTag
from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.room import Room
from app.models.room_project import RoomProject
from app.models.tag import Tag
from app.services import llm_client

logger = logging.getLogger(__name__)

ADJACENCY_SYSTEM_PROMPT = """Ты AI-ассистент для организации Demo Day. Тебе дан список тегов AI/ML проектов.
Определи семантически близкие пары тегов в контексте Demo Day AI-проектов.
Близкие = эксперт с одним тегом может квалифицированно оценить проект с другим.

Верни JSON строго в формате:
{"adjacency": [["tag_a", "tag_b"], ...]}
Только пары из данного списка. Максимум 2-3 смежных тега для каждого."""


async def get_approved_clustering(session: AsyncSession, event_id) -> ClusteringRun | None:
    """Get the latest approved clustering run for the event."""
    result = await session.execute(
        select(ClusteringRun)
        .where(ClusteringRun.event_id == event_id)
        .where(ClusteringRun.status == "approved")
        .order_by(ClusteringRun.approved_at.desc())
        .options(
            selectinload(ClusteringRun.rooms)
            .selectinload(Room.project_assignments)
            .selectinload(RoomProject.project)
            .selectinload(Project.tags)
            .selectinload(ProjectTag.tag)
        )
        .limit(1)
    )
    return result.scalars().first()


async def get_room_tags(
    session: AsyncSession, clustering_run_id
) -> dict[uuid.UUID, tuple[Room, set[str]]]:
    """For each room, compute tag set as union of project tags."""
    result = await session.execute(
        select(Room)
        .where(Room.clustering_run_id == clustering_run_id)
        .options(
            selectinload(Room.project_assignments)
            .selectinload(RoomProject.project)
            .selectinload(Project.tags)
            .selectinload(ProjectTag.tag)
        )
    )
    rooms = result.scalars().all()

    room_tags: dict[uuid.UUID, tuple[Room, set[str]]] = {}
    for room in rooms:
        tags = set()
        for rp in room.project_assignments:
            for pt in rp.project.tags:
                tags.add(pt.tag.name)
        room_tags[room.id] = (room, tags)

    return room_tags


async def compute_idf_weights(session: AsyncSession, event_id) -> dict[str, float]:
    """Compute IDF weight for each tag: log(total_experts / experts_with_tag)."""
    # Total experts with at least one tag
    total_result = await session.execute(
        select(func.count(func.distinct(ExpertTag.expert_id)))
        .join(Expert, Expert.id == ExpertTag.expert_id)
        .where(Expert.event_id == event_id)
    )
    total_experts = total_result.scalar() or 1

    # Count experts per tag
    tag_counts_result = await session.execute(
        select(Tag.name, func.count(func.distinct(ExpertTag.expert_id)))
        .join(ExpertTag, ExpertTag.tag_id == Tag.id)
        .join(Expert, Expert.id == ExpertTag.expert_id)
        .where(Expert.event_id == event_id)
        .group_by(Tag.name)
    )

    idf: dict[str, float] = {}
    for tag_name, count in tag_counts_result.all():
        idf[tag_name] = math.log(total_experts / max(count, 1))

    return idf


async def resolve_adjacent_tags(all_tags: list[str]) -> dict[str, set[str]]:
    """Single LLM call to get adjacent tag pairs. Returns adjacency map."""
    if not all_tags:
        return {}

    user_prompt = f"Список тегов: {json.dumps(all_tags, ensure_ascii=False)}"

    try:
        response = await llm_client.send_chat_completion(
            system_prompt=ADJACENCY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            json_mode=True,
        )

        adjacency: dict[str, set[str]] = {}
        tag_set = set(all_tags)

        for pair in response.get("adjacency", []):
            if len(pair) == 2 and pair[0] in tag_set and pair[1] in tag_set:
                adjacency.setdefault(pair[0], set()).add(pair[1])
                adjacency.setdefault(pair[1], set()).add(pair[0])

        logger.info("Adjacent tags resolved: %d pairs", sum(len(v) for v in adjacency.values()) // 2)
        return adjacency

    except Exception:
        logger.warning("LLM adjacent tag resolution failed, using exact matches only")
        return {}


async def run_matching(
    session: AsyncSession, event_id, use_adjacent_tags: bool = True
) -> dict:
    """Run weighted tag-overlap matching. Returns matching result dict."""

    # 1. Get approved clustering
    clustering = await get_approved_clustering(session, event_id)
    if not clustering:
        raise ValueError("No approved clustering found. Approve a clustering run first.")

    # 2. Delete existing proposed assignments for this clustering run
    await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status == "proposed")
    )
    # Actually delete
    from sqlalchemy import delete
    await session.execute(
        delete(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status == "proposed")
    )

    # 3. Get room tags
    room_tags = await get_room_tags(session, clustering.id)

    # 4. Compute IDF weights
    idf = await compute_idf_weights(session, event_id)

    # 5. Resolve adjacent tags (optional)
    all_tag_names = list(idf.keys())
    adjacency = {}
    if use_adjacent_tags and all_tag_names:
        adjacency = await resolve_adjacent_tags(all_tag_names)

    # 6. Get all experts with tags
    experts_result = await session.execute(
        select(Expert)
        .where(Expert.event_id == event_id)
        .options(selectinload(Expert.tags).selectinload(ExpertTag.tag))
    )
    all_experts = experts_result.scalars().all()

    # Track room assignment counts for tie-breaking
    room_counts: dict[uuid.UUID, int] = {rid: 0 for rid in room_tags}

    matched = 0
    unmatched = 0
    assignments = []

    for expert in all_experts:
        expert_tag_names = [et.tag.name for et in expert.tags]
        if not expert_tag_names:
            unmatched += 1
            continue

        # Score each room
        best_room_id = None
        best_score = -1.0
        best_matching_tags = []

        for room_id, (room, r_tags) in room_tags.items():
            score = 0.0
            matching = []
            adjacent_tags = set()
            for rt in r_tags:
                adjacent_tags.update(adjacency.get(rt, set()))

            for tag_name in expert_tag_names:
                weight = idf.get(tag_name, 1.0)
                if tag_name in r_tags:
                    score += weight * 1.0
                    matching.append(tag_name)
                elif tag_name in adjacent_tags:
                    score += weight * 0.5
                    matching.append(f"~{tag_name}")

            # Tie-break: prefer less-covered room
            if score > best_score or (
                score == best_score
                and best_room_id is not None
                and room_counts.get(room_id, 0) < room_counts.get(best_room_id, 0)
            ):
                best_score = score
                best_room_id = room_id
                best_matching_tags = matching

        if best_room_id and best_score > 0:
            assignment = ExpertRoomAssignment(
                expert_id=expert.id,
                room_id=best_room_id,
                clustering_run_id=clustering.id,
                match_score=round(best_score, 3),
                status="proposed",
            )
            session.add(assignment)
            assignments.append((expert, assignment, best_matching_tags))
            room_counts[best_room_id] = room_counts.get(best_room_id, 0) + 1
            matched += 1
        else:
            unmatched += 1

    await session.commit()

    # Normalize scores to 0-1 range
    max_score = max((asgn.match_score for _, asgn, _ in assignments), default=1.0) or 1.0

    # Build result
    rooms_result = []
    for room_id, (room, _) in room_tags.items():
        room_experts = [
            {
                "expert_id": str(exp.id),
                "name": exp.name,
                "match_score": round(asgn.match_score / max_score, 3),
                "matching_tags": tags,
                "is_manual": asgn.is_manual,
            }
            for exp, asgn, tags in assignments
            if asgn.room_id == room_id
        ]
        rooms_result.append({
            "room_id": str(room.id),
            "room_name": room.name,
            "expert_count": len(room_experts),
            "experts": sorted(room_experts, key=lambda x: x["match_score"], reverse=True),
        })

    return {
        "clustering_run_id": str(clustering.id),
        "total_experts": len(all_experts),
        "matched_experts": matched,
        "unmatched_experts": unmatched,
        "rooms": sorted(rooms_result, key=lambda r: r["room_name"]),
    }


async def move_expert(
    session: AsyncSession, assignment_id, target_room_id
) -> ExpertRoomAssignment | None:
    """Move expert to a different room."""
    result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.id == assignment_id)
        .options(selectinload(ExpertRoomAssignment.room))
    )
    assignment = result.scalars().first()
    if not assignment:
        return None

    assignment.room_id = target_room_id
    assignment.is_manual = True
    # Recalculate score would require re-running the scoring — set to 0 for manual
    assignment.match_score = 0.0
    await session.commit()

    # Reload with new room
    result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.id == assignment_id)
        .options(selectinload(ExpertRoomAssignment.room))
    )
    return result.scalars().first()


async def approve_matching(session: AsyncSession, clustering_run_id) -> int:
    """Approve all proposed assignments for a clustering run."""
    result = await session.execute(
        update(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.clustering_run_id == clustering_run_id)
        .where(ExpertRoomAssignment.status == "proposed")
        .values(status="approved")
        .returning(ExpertRoomAssignment.id)
    )
    count = len(result.all())
    await session.commit()
    return count


async def get_current_matching(session: AsyncSession, event_id) -> dict | None:
    """Get current matching result for the approved clustering."""
    clustering = await get_approved_clustering(session, event_id)
    if not clustering:
        return None

    # Get all assignments for this clustering run
    assignments_result = await session.execute(
        select(ExpertRoomAssignment)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .options(
            selectinload(ExpertRoomAssignment.expert)
            .selectinload(Expert.tags)
            .selectinload(ExpertTag.tag),
            selectinload(ExpertRoomAssignment.room),
        )
    )
    assignments = assignments_result.scalars().all()

    # Get rooms
    room_tags = await get_room_tags(session, clustering.id)

    # Normalize scores to 0-1 range
    max_score = max((a.match_score for a in assignments), default=1.0) or 1.0

    # Group by room
    rooms_result = []
    for room_id, (room, _) in room_tags.items():
        room_assignments = [a for a in assignments if a.room_id == room_id]
        experts = []
        for a in room_assignments:
            tag_names = [et.tag.name for et in a.expert.tags]
            experts.append({
                "expert_id": str(a.expert.id),
                "name": a.expert.name,
                "match_score": round(a.match_score / max_score, 3),
                "matching_tags": tag_names,
                "is_manual": a.is_manual,
                "status": a.status,
            })
        rooms_result.append({
            "room_id": str(room.id),
            "room_name": room.name,
            "expert_count": len(experts),
            "experts": sorted(experts, key=lambda x: x["match_score"], reverse=True),
        })

    total_experts_result = await session.execute(
        select(func.count(Expert.id)).where(Expert.event_id == event_id)
    )
    total = total_experts_result.scalar() or 0

    return {
        "clustering_run_id": str(clustering.id),
        "total_experts": total,
        "matched_experts": len(assignments),
        "unmatched_experts": total - len(assignments),
        "rooms": sorted(rooms_result, key=lambda r: r["room_name"]),
    }
