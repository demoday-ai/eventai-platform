"""Test organizer and business partner workflows."""
import asyncio
import json
from datetime import date, timedelta

async def main():
    from app.database import async_session
    from app.models import Event, User, UserRole, Role, Project
    from app.models.business_profile import BusinessProfile, BusinessObjective
    from app.services import project_service, clustering_service, schedule_service
    from app.services import recommendation_service
    from sqlalchemy import text, select
    from app.models.room import Room
    from app.models.room_project import RoomProject

    print("=" * 60)
    print("WORKFLOW TEST: Organizer + Business Partner")
    print("=" * 60)

    async with async_session() as session:
        # 1. Clear and create fresh event
        print("\n[1] Clearing database and creating event...")
        await session.execute(text("TRUNCATE TABLE schedule_slots, schedule_change_logs, room_projects, rooms, clustering_runs, project_tags, projects, business_profiles, project_recommendations, notifications, user_roles, users, events, roles, tags CASCADE"))
        await session.commit()

        # Create roles
        roles_data = [
            ("organizer", "Организатор"),
            ("student", "Студент"),
            ("expert", "Эксперт"),
            ("guest", "Гость"),
            ("business", "Бизнес-партнёр"),
        ]
        for code, name in roles_data:
            role = Role(code=code, name=name)
            session.add(role)

        # Create event
        event = Event(
            name="Demo Day Test",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        print(f"   Created event: {event.name} (ID: {event.id})")

        # 2. Load projects from seed file
        print("\n[2] Loading projects from seed file...")
        with open("data/seed/projects_seed.json", "rb") as f:
            content = f.read()

        rows = project_service.parse_json(content)
        # Load first 50 projects for faster test
        rows = rows[:50]

        valid_rows, errors, duplicates = project_service.validate_rows(rows)
        if errors:
            print(f"   Validation errors: {len(errors)}")
        count = await project_service.save_projects(session, event.id, valid_rows)
        print(f"   Loaded {count} projects")

        # 3. Run clustering (6 rooms)
        print("\n[3] Running AI clustering (6 rooms)...")
        try:
            clustering_run = await clustering_service.run_clustering(
                session, event.id, num_rooms=6
            )
            await session.commit()
            await session.refresh(clustering_run)
            print(f"   Clustering done! Run ID: {clustering_run.id}")
            print(f"   Status: {clustering_run.status}")
            print(f"   Rooms created: {clustering_run.num_rooms}")

            # Show rooms summary
            result = await session.execute(
                select(Room).where(Room.clustering_run_id == clustering_run.id)
            )
            rooms = result.scalars().all()
            print(f"\n   Rooms:")
            for room in rooms:
                rp_count = await session.execute(
                    select(RoomProject).where(RoomProject.room_id == room.id)
                )
                count = len(rp_count.scalars().all())
                print(f"     - {room.name}: {count} projects")

        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return

        # 4. Approve clustering
        print("\n[4] Approving clustering...")
        clustering_run.status = "approved"
        await session.commit()
        print(f"   Status updated to: {clustering_run.status}")

        # 5. Generate schedule
        print("\n[5] Generating schedule...")
        try:
            result = await schedule_service.generate_schedule(
                session, event.id, clustering_run.id
            )
            await session.commit()
            print(f"   Created {result.total_slots} slots")
            print(f"   Rooms: {len(result.rooms)}")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 60)
        print("ORGANIZER WORKFLOW: COMPLETE")
        print("=" * 60)

        # ============ BUSINESS PARTNER WORKFLOW ============

        print("\n" + "=" * 60)
        print("BUSINESS PARTNER WORKFLOW")
        print("=" * 60)

        # 6. Create test business user
        print("\n[6] Creating test business user...")
        user = User(
            telegram_user_id="123456789",
            username="test_partner",
            full_name="Test Partner",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Assign business role
        role_result = await session.execute(
            select(Role).where(Role.code == "business")
        )
        business_role = role_result.scalars().first()
        user_role = UserRole(user_id=user.id, role_id=business_role.id, event_id=event.id)
        session.add(user_role)
        await session.commit()
        print(f"   Created user: {user.full_name} with business role")

        # 7. Create business profile
        print("\n[7] Creating business profile...")
        profile = BusinessProfile(
            user_id=user.id,
            event_id=event.id,
            objective=BusinessObjective.TECHNOLOGY,
            industries=["EdTech", "AI"],
            tech_stack=["NLP", "LLM", "RAG"],
            project_stages=["MVP", "Prototype"],
            collaboration_format="Partnership",
            free_text_raw="Ищем проекты в сфере образования с использованием LLM",
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        print(f"   Profile created!")
        print(f"   - Objective: {profile.objective.value}")
        print(f"   - Industries: {profile.industries}")
        print(f"   - Tech stack: {profile.tech_stack}")

        # 8. Generate recommendations
        print("\n[8] Generating project recommendations...")
        try:
            recommendations = await recommendation_service.generate_recommendations(
                session, profile, max_results=10
            )
            await session.commit()
            print(f"   Generated {len(recommendations)} recommendations:")
            for i, rec in enumerate(recommendations[:5], 1):
                # Get project
                proj_result = await session.execute(
                    select(Project).where(Project.id == rec.project_id)
                )
                project = proj_result.scalars().first()
                print(f"     {i}. {project.title[:40]}... (score: {rec.relevance_score})")
                if rec.relevance_explanation:
                    print(f"        -> {rec.relevance_explanation[:60]}...")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 60)
        print("BUSINESS PARTNER WORKFLOW: COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
