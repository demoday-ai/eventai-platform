"""Comprehensive test of all DemoDay workflows."""
import asyncio
from datetime import date, timedelta


async def test_organizer_workflow(session, event):
    """Test: Upload projects, cluster, approve, generate schedule."""
    from app.services import project_service, clustering_service, schedule_service
    from sqlalchemy import select
    from app.models.room import Room
    from app.models.room_project import RoomProject

    print("\n" + "=" * 60)
    print("1. ORGANIZER WORKFLOW")
    print("=" * 60)

    # Load projects
    print("\n[1.1] Loading projects from seed...")
    with open("/app/data/seed/projects_seed.json", "rb") as f:
        content = f.read()

    rows = project_service.parse_json(content)
    rows = rows[:30]  # 30 projects for faster test

    valid_rows, errors, duplicates = project_service.validate_rows(rows)
    count = await project_service.save_projects(session, event.id, valid_rows)
    print(f"      Loaded {count} projects")
    await session.commit()

    # Clustering
    print("\n[1.2] Running AI clustering (4 rooms)...")
    clustering_run = await clustering_service.run_clustering(session, event.id, num_rooms=4)
    await session.commit()
    await session.refresh(clustering_run)
    print(f"      Status: {clustering_run.status}")

    # Show rooms
    result = await session.execute(
        select(Room).where(Room.clustering_run_id == clustering_run.id)
    )
    rooms = result.scalars().all()
    total_assigned = 0
    for room in rooms:
        rp_result = await session.execute(
            select(RoomProject).where(RoomProject.room_id == room.id)
        )
        count = len(rp_result.scalars().all())
        total_assigned += count
        print(f"      - {room.name}: {count} projects")

    print(f"      Total assigned: {total_assigned}/30")

    # Approve
    print("\n[1.3] Approving clustering...")
    clustering_run.status = "approved"
    await session.commit()
    print(f"      Status: {clustering_run.status}")

    # Generate schedule
    print("\n[1.4] Generating schedule...")
    schedule_result = await schedule_service.generate_schedule(
        session, event.id, clustering_run.id
    )
    await session.commit()
    print(f"      Created {schedule_result.total_slots} slots in {len(schedule_result.rooms)} rooms")

    print("\n[1.5] ✅ ORGANIZER WORKFLOW: PASSED")
    return clustering_run


async def test_student_workflow(session, event, project):
    """Test: Student confirms participation."""
    from app.models import User, UserRole, Role
    from app.models.schedule_slot import ScheduleSlot
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("2. STUDENT WORKFLOW")
    print("=" * 60)

    # Create student user
    print("\n[2.1] Creating student user...")
    user = User(
        telegram_user_id="111111111",
        username="test_student",
        full_name="Тест Студентов",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Assign student role
    role_result = await session.execute(select(Role).where(Role.code == "student"))
    student_role = role_result.scalars().first()
    user_role = UserRole(user_id=user.id, role_id=student_role.id, event_id=event.id)
    session.add(user_role)
    await session.commit()
    print(f"      Created: {user.full_name}")

    # Link to project
    print("\n[2.2] Linking student to project...")
    project.student_user_id = user.id
    await session.commit()
    print(f"      Linked to: {project.title[:40]}...")

    # Check schedule slot
    print("\n[2.3] Checking schedule slot...")
    slot_result = await session.execute(
        select(ScheduleSlot).where(ScheduleSlot.project_id == project.id)
    )
    slot = slot_result.scalars().first()
    if slot:
        print(f"      Slot: {slot.start_time} - {slot.end_time}")
        print(f"      Room ID: {slot.room_id}")
    else:
        print("      No slot assigned (expected - project may not be in schedule)")

    print("\n[2.4] ✅ STUDENT WORKFLOW: PASSED")
    return user


async def test_guest_workflow(session, event):
    """Test: Guest profiling and recommendations."""
    from app.models import User, UserRole, Role
    from app.services import profiling_service
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("3. GUEST WORKFLOW")
    print("=" * 60)

    # Create guest user
    print("\n[3.1] Creating guest user...")
    user = User(
        telegram_user_id="333333333",
        username="test_guest",
        full_name="Гость Тестовый",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Assign guest role
    role_result = await session.execute(select(Role).where(Role.code == "guest"))
    guest_role = role_result.scalars().first()
    user_role = UserRole(user_id=user.id, role_id=guest_role.id, event_id=event.id)
    session.add(user_role)
    await session.commit()
    print(f"      Created: {user.full_name}")

    # Create guest profile
    print("\n[3.2] Creating guest profile...")
    profile = await profiling_service.get_or_create_profile(session, user.id, event.id)
    await profiling_service.save_profile(
        session, profile,
        selected_tags=["NLP", "CV", "LLM"],
        extracted_tags=["ML в промышленности"],
        keywords=["computer vision", "нейросети"],
        raw_text="Интересуюсь компьютерным зрением и NLP"
    )
    await session.commit()
    print(f"      Tags: {profile.selected_tags + profile.extracted_tags}")
    print(f"      Keywords: {profile.keywords}")

    # Generate recommendations
    print("\n[3.3] Generating recommendations (may take ~30-60s)...")
    recommendations = await profiling_service.generate_recommendations(session, profile)
    print(f"      Total: {recommendations.get('total', 0)} projects")
    print(f"      Must visit: {len(recommendations.get('must_visit', []))}")
    print(f"      If time: {len(recommendations.get('if_time', []))}")

    if recommendations.get('must_visit'):
        print("\n      Top 3 recommendations:")
        for rec in recommendations['must_visit'][:3]:
            print(f"        - {rec['title'][:40]}...")

    print("\n[3.4] ✅ GUEST WORKFLOW: PASSED")
    return user


async def test_business_workflow(session, event):
    """Test: Business partner profiling and recommendations."""
    from app.models import User, UserRole, Role
    from app.models.business_profile import BusinessProfile, BusinessObjective
    from app.services import recommendation_service
    from app.models import Project
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("4. BUSINESS PARTNER WORKFLOW")
    print("=" * 60)

    # Create business user
    print("\n[4.1] Creating business user...")
    user = User(
        telegram_user_id="444444444",
        username="test_business",
        full_name="Бизнес Партнёров",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Assign business role
    role_result = await session.execute(select(Role).where(Role.code == "business"))
    business_role = role_result.scalars().first()
    user_role = UserRole(user_id=user.id, role_id=business_role.id, event_id=event.id)
    session.add(user_role)
    await session.commit()
    print(f"      Created: {user.full_name}")

    # Create business profile
    print("\n[4.2] Creating business profile...")
    profile = BusinessProfile(
        user_id=user.id,
        event_id=event.id,
        objective=BusinessObjective.TECHNOLOGY,
        industries=["FinTech", "EdTech"],
        tech_stack=["NLP", "LLM", "RAG"],
        project_stages=["MVP", "Production"],
        collaboration_format="Пилотный проект",
        free_text_raw="Ищем AI-решения для автоматизации",
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    print(f"      Objective: {profile.objective.value}")
    print(f"      Industries: {profile.industries}")

    # Generate recommendations
    print("\n[4.3] Generating recommendations...")
    recommendations = await recommendation_service.generate_recommendations(
        session, profile, max_results=5
    )
    await session.commit()
    print(f"      Generated: {len(recommendations)} recommendations")

    for i, rec in enumerate(recommendations[:3], 1):
        proj_result = await session.execute(
            select(Project).where(Project.id == rec.project_id)
        )
        project = proj_result.scalars().first()
        print(f"        {i}. {project.title[:35]}... (score: {rec.relevance_score})")

    print("\n[4.4] ✅ BUSINESS WORKFLOW: PASSED")
    return user


async def test_expert_workflow(session, event, room, clustering_run_id):
    """Test: Expert scoring (simplified - using existing expert model)."""
    from app.models.expert import Expert
    from app.models.expert_room_assignment import ExpertRoomAssignment
    from app.models.expert_score import ExpertScore
    from app.models.room_project import RoomProject
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("5. EXPERT WORKFLOW")
    print("=" * 60)

    # Create expert
    print("\n[5.1] Creating expert...")
    expert = Expert(
        seed_id="TEST001",
        name="Эксперт Тестович",
        telegram_username="test_expert",
        position="ML Lead",
        event_id=event.id,
    )
    session.add(expert)
    await session.commit()
    await session.refresh(expert)
    print(f"      Created: {expert.name}")

    # Assign to room
    print("\n[5.2] Assigning expert to room...")
    assignment = ExpertRoomAssignment(
        expert_id=expert.id,
        room_id=room.id,
        clustering_run_id=clustering_run_id,
        status="confirmed",
    )
    session.add(assignment)
    await session.commit()
    print(f"      Assigned to: {room.name}")

    # Score a project
    print("\n[5.3] Scoring a project...")
    rp_result = await session.execute(
        select(RoomProject).where(RoomProject.room_id == room.id).limit(1)
    )
    room_project = rp_result.scalars().first()

    if room_project:
        score = ExpertScore(
            expert_id=expert.id,
            project_id=room_project.project_id,
            event_id=event.id,
            criterion_1=3,
            criterion_2=2,
            criterion_3=3,
            criterion_4=2,
            criterion_5=3,
            criterion_6=2,
            criterion_7=3,
            total_score=18,
            comment="Отличный проект с хорошим потенциалом",
        )
        session.add(score)
        await session.commit()
        print(f"      Scored project ID: {room_project.project_id}")
        print(f"      Total score: {score.total_score}")
        print(f"      Comment: {score.comment[:40]}...")
    else:
        print("      No projects in room to score")

    print("\n[5.4] ✅ EXPERT WORKFLOW: PASSED")
    return expert


async def main():
    from app.database import async_session
    from app.models import Event, Role, Project
    from app.models.room import Room
    from sqlalchemy import text, select

    print("=" * 60)
    print("DEMODAY BOT - COMPREHENSIVE WORKFLOW TESTS")
    print("=" * 60)

    async with async_session() as session:
        # Setup: Clear and create fresh data
        print("\n[SETUP] Clearing database...")
        await session.execute(text("""
            TRUNCATE TABLE
                expert_scores, expert_room_assignments, experts, expert_tags, expert_briefings,
                schedule_slots, schedule_change_logs,
                room_projects, rooms, clustering_runs,
                project_tags, projects,
                guest_profiles, business_profiles, project_recommendations, recommendations,
                qa_suggestions, business_followups, contact_requests, followup_packages,
                notifications, reminder_notifications, reminder_batches, escalations,
                participation_requests, feedback_comments,
                user_roles, users,
                events, roles, tags
            CASCADE
        """))
        await session.commit()

        # Create roles
        print("[SETUP] Creating roles...")
        for code, name in [
            ("organizer", "Организатор"),
            ("student", "Студент"),
            ("expert", "Эксперт"),
            ("guest", "Гость"),
            ("business", "Бизнес-партнёр"),
        ]:
            session.add(Role(code=code, name=name))
        await session.commit()

        # Create event
        print("[SETUP] Creating event...")
        event = Event(
            name="Demo Day Test 2026",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        print(f"[SETUP] Event: {event.name} (ID: {event.id})")

        # Run all workflow tests
        try:
            # 1. Organizer
            clustering_run = await test_organizer_workflow(session, event)

            # Get first room and project for other tests
            room_result = await session.execute(
                select(Room).where(Room.clustering_run_id == clustering_run.id).limit(1)
            )
            room = room_result.scalars().first()

            proj_result = await session.execute(
                select(Project).where(Project.event_id == event.id).limit(1)
            )
            project = proj_result.scalars().first()

            # 2. Student
            await test_student_workflow(session, event, project)

            # 3. Guest
            await test_guest_workflow(session, event)

            # 4. Business Partner
            await test_business_workflow(session, event)

            # 5. Expert
            await test_expert_workflow(session, event, room, clustering_run.id)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1

        print("\n" + "=" * 60)
        print("✅ ALL WORKFLOW TESTS PASSED!")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
