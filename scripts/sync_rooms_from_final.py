"""Sync room assignments from projects_final.json to database.

Creates rooms and room_project assignments based on the schedule data.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import async_session
from app.models.event import Event
from app.models.project import Project
from app.models.clustering_run import ClusteringRun
from app.models.room import Room
from app.models.room_project import RoomProject


async def get_event(session: AsyncSession) -> Event | None:
    """Get the first event."""
    result = await session.execute(select(Event).limit(1))
    return result.scalars().first()


async def sync_rooms(session: AsyncSession, event_id, final_data: list) -> dict:
    """Sync rooms and assignments from final data."""

    # 1. Collect unique rooms from final data
    all_rooms = set()
    for proj in final_data:
        rooms_str = proj.get("rooms", "")
        if rooms_str:
            for r in rooms_str.split(";"):
                r = r.strip()
                if r:
                    all_rooms.add(r)

    print(f"Found {len(all_rooms)} unique rooms in final data:")
    for r in sorted(all_rooms):
        print(f"  - {r}")

    # 2. Check for existing approved clustering
    existing_run = await session.scalar(
        select(ClusteringRun)
        .where(ClusteringRun.event_id == event_id)
        .where(ClusteringRun.status == "approved")
    )

    if existing_run:
        print(f"\nExisting approved clustering run found: {existing_run.id}")
        # Delete existing rooms (cascade deletes room_projects)
        await session.execute(
            select(Room).where(Room.clustering_run_id == existing_run.id)
        )
        # Actually need to delete
        from sqlalchemy import delete
        await session.execute(
            delete(Room).where(Room.clustering_run_id == existing_run.id)
        )
        clustering_run = existing_run
    else:
        # Create new clustering run
        clustering_run = ClusteringRun(
            event_id=event_id,
            num_rooms=len(all_rooms),
            status="approved",
            feedback="Импорт из расписания Excel",
            llm_model="manual-import",
            approved_at=datetime.now(timezone.utc),
            schedule_approved_at=datetime.now(timezone.utc),
        )
        session.add(clustering_run)
        await session.flush()
        print(f"\nCreated new clustering run: {clustering_run.id}")

    # 3. Create rooms
    room_map = {}  # room_name -> Room
    for idx, room_name in enumerate(sorted(all_rooms)):
        # Determine theme from room name
        theme = room_name
        if "Комната" in room_name:
            # Map Комната N to themes from schedule
            room_themes = {
                "Комната 1": "EdTech",
                "Комната 2": "RecSys",
                "Комната 3": "LLM/VLM",
                "Комната 4": "NLP",
                "Комната 5": "ML в промышленности",
                "Комната 6": "FinTech",
            }
            theme = room_themes.get(room_name, room_name)
        elif "Research" in room_name:
            research_themes = {
                "Research 1": "Audio",
                "Research 2": "Security",
                "Research 3": "NLP",
                "Research 4": "Agents",
            }
            theme = research_themes.get(room_name, room_name)

        room = Room(
            clustering_run_id=clustering_run.id,
            name=room_name,
            theme_rationale=theme,
            display_order=idx,
        )
        session.add(room)
        await session.flush()
        room_map[room_name] = room
        print(f"  Created room: {room_name} (theme: {theme})")

    # 4. Build project title -> id map
    result = await session.execute(
        select(Project.id, Project.title).where(Project.event_id == event_id)
    )
    project_map = {}  # normalized title -> project_id
    for pid, title in result.all():
        key = title.lower().strip()
        project_map[key] = pid

    print(f"\n{len(project_map)} projects in database")

    # 5. Create room_project assignments
    assigned = 0
    not_found = []

    for proj in final_data:
        title = proj.get("title", "").strip()
        rooms_str = proj.get("rooms", "")

        if not title or not rooms_str:
            continue

        # Find project in DB
        key = title.lower().strip()
        project_id = project_map.get(key)

        if not project_id:
            # Try partial match
            for db_key, pid in project_map.items():
                if key[:30] in db_key or db_key[:30] in key:
                    project_id = pid
                    break

        if not project_id:
            not_found.append(title[:50])
            continue

        # Assign to each room
        for room_name in rooms_str.split(";"):
            room_name = room_name.strip()
            if not room_name or room_name not in room_map:
                continue

            room = room_map[room_name]
            rp = RoomProject(
                room_id=room.id,
                project_id=project_id,
            )
            session.add(rp)
            assigned += 1

    await session.commit()

    print(f"\nAssigned {assigned} project-room links")
    if not_found:
        print(f"Could not find {len(not_found)} projects:")
        for t in not_found[:10]:
            print(f"  - {t}")
        if len(not_found) > 10:
            print(f"  ... and {len(not_found) - 10} more")

    return {
        "rooms_created": len(room_map),
        "assignments": assigned,
        "not_found": len(not_found),
    }


async def main():
    # Load final data
    data_path = Path(__file__).parent.parent / "data" / "projects_final.json"
    if not data_path.exists():
        print(f"ERROR: {data_path} not found")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        final_data = json.load(f)

    print(f"Loaded {len(final_data)} projects from projects_final.json")

    async with async_session() as session:
        event = await get_event(session)
        if not event:
            print("ERROR: No event found")
            return

        print(f"Event: {event.name} ({event.id})")

        result = await sync_rooms(session, event.id, final_data)
        print("\n=== RESULT ===")
        print(f"Rooms: {result['rooms_created']}")
        print(f"Assignments: {result['assignments']}")
        print(f"Not found: {result['not_found']}")


if __name__ == "__main__":
    asyncio.run(main())
