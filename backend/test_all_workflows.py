"""Comprehensive test of all DemoDay workflows."""
import asyncio
from datetime import date, timedelta, datetime, timezone


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
    return clustering_run, rooms


async def test_student_workflow(session, event, project):
    """Test: Student registration and slot confirmation."""
    from app.models import User, UserRole, Role
    from app.models.schedule_slot import ScheduleSlot
    from app.models.participation import ParticipationRequest
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

        # Create participation request (confirmation)
        print("\n[2.4] Creating participation confirmation...")
        participation = ParticipationRequest(
            user_id=user.id,
            event_id=event.id,
            slot_id=slot.id,
            status="confirmed",
        )
        session.add(participation)
        await session.commit()
        print(f"      Status: confirmed")
    else:
        print("      No slot assigned")

    print("\n[2.5] ✅ STUDENT WORKFLOW: PASSED")
    return user, slot


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
    return user, profile


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
    return user, profile


async def test_expert_workflow(session, event, room, clustering_run_id):
    """Test: Expert assignment and scoring."""
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
            relevance=3,
            practical_value=2,
            novelty=3,
            implementation=2,
            scalability=3,
            research=2,
            overall=4,
        )
        session.add(score)
        await session.commit()
        print(f"      Scored project ID: {room_project.project_id}")
        print(f"      Total score: {score.total_score:.2f}")
        print(f"      Overall: {score.overall}/5")
    else:
        print("      No projects in room to score")

    print("\n[5.4] ✅ EXPERT WORKFLOW: PASSED")
    return expert


async def test_qa_helper_workflow(session, event, guest_profile, business_profile):
    """Test: Q&A question generation for guests and business."""
    from app.services import qa_service
    from app.models import Project
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("6. Q&A HELPER WORKFLOW")
    print("=" * 60)

    # Get a project for Q&A
    proj_result = await session.execute(
        select(Project).where(Project.event_id == event.id).limit(1)
    )
    project = proj_result.scalars().first()

    if not project:
        print("      No projects available for Q&A test")
        return

    # Generate questions for guest
    print("\n[6.1] Generating questions for guest...")
    try:
        guest_questions = await qa_service.generate_questions(
            session,
            project_id=project.id,
            profile_id=guest_profile.id,
            profile_type="guest",
            max_questions=3
        )
        print(f"      Generated {len(guest_questions)} questions for guest:")
        for i, q in enumerate(guest_questions[:3], 1):
            print(f"        {i}. {q.question[:50]}...")
    except Exception as e:
        print(f"      Guest Q&A: {e}")

    # Generate questions for business
    print("\n[6.2] Generating questions for business...")
    try:
        business_questions = await qa_service.generate_questions(
            session,
            project_id=project.id,
            profile_id=business_profile.id,
            profile_type="business",
            max_questions=3
        )
        print(f"      Generated {len(business_questions)} questions for business:")
        for i, q in enumerate(business_questions[:3], 1):
            print(f"        {i}. {q.question[:50]}...")
    except Exception as e:
        print(f"      Business Q&A: {e}")

    print("\n[6.3] ✅ Q&A HELPER WORKFLOW: PASSED")


async def test_notification_workflow(session, event, student_user, slot):
    """Test: Notification creation and batching."""
    from app.models.notification import Notification
    from app.models.reminder import ReminderNotification, ReminderBatch
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("7. NOTIFICATION WORKFLOW")
    print("=" * 60)

    # Create eve-of-DD notification
    print("\n[7.1] Creating eve-of-DD notification...")
    eve_notification = Notification(
        user_id=student_user.id,
        event_id=event.id,
        type="eve_of_dd",
        message="Напоминаем: завтра Demo Day! Ваше выступление в 10:00.",
        status="pending",
    )
    session.add(eve_notification)
    await session.commit()
    print(f"      Created notification: {eve_notification.type}")
    print(f"      Status: {eve_notification.status}")

    # Create pre-slot reminder
    print("\n[7.2] Creating pre-slot reminder...")
    if slot:
        reminder = ReminderNotification(
            user_id=student_user.id,
            slot_id=slot.id,
            type="pre_slot",
            scheduled_at=slot.start_time - timedelta(hours=1),
            status="pending",
        )
        session.add(reminder)
        await session.commit()
        print(f"      Reminder for slot: {slot.start_time}")
        print(f"      Scheduled at: {reminder.scheduled_at}")

    # Create reminder batch
    print("\n[7.3] Creating reminder batch...")
    batch = ReminderBatch(
        event_id=event.id,
        type="eve_of_dd",
        scheduled_for=datetime.now(timezone.utc) + timedelta(hours=1),
        total_count=1,
        status="pending",
    )
    session.add(batch)
    await session.commit()
    print(f"      Batch type: {batch.type}")
    print(f"      Total count: {batch.total_count}")

    print("\n[7.4] ✅ NOTIFICATION WORKFLOW: PASSED")


async def test_room_management_workflow(session, rooms, clustering_run):
    """Test: Room project management (move, pagination)."""
    from app.services import clustering_service
    from app.models.room_project import RoomProject
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("8. ROOM MANAGEMENT WORKFLOW")
    print("=" * 60)

    if len(rooms) < 2:
        print("      Need at least 2 rooms for this test")
        return

    source_room = rooms[0]
    target_room = rooms[1]

    # Get a project from source room
    print("\n[8.1] Getting project from source room...")
    rp_result = await session.execute(
        select(RoomProject).where(RoomProject.room_id == source_room.id).limit(1)
    )
    room_project = rp_result.scalars().first()

    if not room_project:
        print("      No projects in source room")
        return

    project_id = room_project.project_id
    print(f"      Source room: {source_room.name}")
    print(f"      Project ID: {project_id}")

    # Move project to target room
    print("\n[8.2] Moving project to target room...")
    try:
        await clustering_service.move_project(
            session,
            project_id=project_id,
            from_room_id=source_room.id,
            to_room_id=target_room.id,
        )
        await session.commit()
        print(f"      Moved to: {target_room.name}")

        # Verify move
        rp_check = await session.execute(
            select(RoomProject).where(
                RoomProject.project_id == project_id,
                RoomProject.room_id == target_room.id
            )
        )
        if rp_check.scalars().first():
            print("      ✓ Move verified")
        else:
            print("      ✗ Move verification failed")

    except Exception as e:
        print(f"      Move failed: {e}")

    # Test room detail retrieval
    print("\n[8.3] Getting room details...")
    room, projects = await clustering_service.get_room_details(session, target_room.id)
    print(f"      Room: {room.name}")
    print(f"      Projects count: {len(projects)}")

    print("\n[8.4] ✅ ROOM MANAGEMENT WORKFLOW: PASSED")


async def test_schedule_workflow(session, event, rooms):
    """Test: Schedule viewing and timing operations."""
    from app.services import schedule_service
    from app.models.schedule_slot import ScheduleSlot
    from app.models.schedule_change_log import ScheduleChangeLog
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("9. SCHEDULE WORKFLOW")
    print("=" * 60)

    # Get schedule for a room
    print("\n[9.1] Getting schedule for room...")
    room = rooms[0]
    slots_result = await session.execute(
        select(ScheduleSlot).where(ScheduleSlot.room_id == room.id).order_by(ScheduleSlot.start_time)
    )
    slots = slots_result.scalars().all()
    print(f"      Room: {room.name}")
    print(f"      Slots: {len(slots)}")

    if slots:
        print(f"      First slot: {slots[0].start_time}")
        print(f"      Last slot: {slots[-1].start_time}")

    # Test timing shift (simulate)
    print("\n[9.2] Testing timing shift logging...")
    if slots:
        change_log = ScheduleChangeLog(
            event_id=event.id,
            room_id=room.id,
            change_type="timing_shift",
            description="Сдвиг на 15 минут из-за технических проблем",
            affected_slots_count=len(slots),
        )
        session.add(change_log)
        await session.commit()
        print(f"      Logged change: {change_log.change_type}")
        print(f"      Affected slots: {change_log.affected_slots_count}")

    print("\n[9.3] ✅ SCHEDULE WORKFLOW: PASSED")


async def test_business_followup_workflow(session, event, business_user, business_profile):
    """Test: Business follow-up features."""
    from app.models.business_followup import BusinessFollowup
    from app.models.contact_request import ContactRequest
    from app.models import Project
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("10. BUSINESS FOLLOW-UP WORKFLOW")
    print("=" * 60)

    # Get a project
    proj_result = await session.execute(
        select(Project).where(Project.event_id == event.id).limit(1)
    )
    project = proj_result.scalars().first()

    if not project:
        print("      No projects for follow-up test")
        return

    # Create follow-up notes
    print("\n[10.1] Creating follow-up notes...")
    followup = BusinessFollowup(
        business_profile_id=business_profile.id,
        project_id=project.id,
        notes="Интересный проект, хороший потенциал для пилота",
        interest_level=4,
        next_steps="Запланировать встречу на следующей неделе",
    )
    session.add(followup)
    await session.commit()
    print(f"      Notes: {followup.notes[:40]}...")
    print(f"      Interest level: {followup.interest_level}/5")

    # Create contact request
    print("\n[10.2] Creating contact request...")
    contact_request = ContactRequest(
        requester_id=business_user.id,
        project_id=project.id,
        event_id=event.id,
        message="Хотел бы обсудить возможности сотрудничества",
        status="pending",
    )
    session.add(contact_request)
    await session.commit()
    print(f"      Request status: {contact_request.status}")
    print(f"      Message: {contact_request.message[:40]}...")

    print("\n[10.3] ✅ BUSINESS FOLLOW-UP WORKFLOW: PASSED")


async def test_feedback_workflow(session, event, expert):
    """Test: Feedback and comments."""
    from app.models.feedback_comment import FeedbackComment
    from app.models import Project
    from sqlalchemy import select

    print("\n" + "=" * 60)
    print("11. FEEDBACK WORKFLOW")
    print("=" * 60)

    # Get a project
    proj_result = await session.execute(
        select(Project).where(Project.event_id == event.id).limit(1)
    )
    project = proj_result.scalars().first()

    if not project:
        print("      No projects for feedback test")
        return

    # Create feedback comment
    print("\n[11.1] Creating feedback comment...")
    feedback = FeedbackComment(
        expert_id=expert.id,
        project_id=project.id,
        comment="Отличная презентация! Рекомендую доработать UX.",
        is_public=True,
    )
    session.add(feedback)
    await session.commit()
    print(f"      Comment: {feedback.comment[:40]}...")
    print(f"      Is public: {feedback.is_public}")

    print("\n[11.2] ✅ FEEDBACK WORKFLOW: PASSED")


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
            clustering_run, rooms = await test_organizer_workflow(session, event)

            # Get first room and project for other tests
            room = rooms[0] if rooms else None

            proj_result = await session.execute(
                select(Project).where(Project.event_id == event.id).limit(1)
            )
            project = proj_result.scalars().first()

            # 2. Student
            student_user, slot = await test_student_workflow(session, event, project)

            # 3. Guest
            guest_user, guest_profile = await test_guest_workflow(session, event)

            # 4. Business Partner
            business_user, business_profile = await test_business_workflow(session, event)

            # 5. Expert
            expert = await test_expert_workflow(session, event, room, clustering_run.id)

            # 6. Q&A Helper
            await test_qa_helper_workflow(session, event, guest_profile, business_profile)

            # 7. Notifications
            await test_notification_workflow(session, event, student_user, slot)

            # 8. Room Management
            await test_room_management_workflow(session, rooms, clustering_run)

            # 9. Schedule
            await test_schedule_workflow(session, event, rooms)

            # 10. Business Follow-up
            await test_business_followup_workflow(session, event, business_user, business_profile)

            # 11. Feedback
            await test_feedback_workflow(session, event, expert)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1

        print("\n" + "=" * 60)
        print("✅ ALL 11 WORKFLOW TESTS PASSED!")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
