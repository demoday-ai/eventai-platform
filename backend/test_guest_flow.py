"""Test guest + business partner profiling flow on live data (non-destructive).

Creates temporary test users → profiles → recommendations → cleanup.
Tests: tag-based scoring, text-search scoring, skip-profiling, business partner with extra_data.
"""
import asyncio
import uuid


async def main():
    from sqlalchemy import delete, select, text

    from app.database import async_session
    from app.models import Event, Role, User, UserRole
    from app.models.guest_profile import GuestProfile
    from app.models.recommendation import Recommendation
    from app.services import profiling_service

    TEST_TG_ID = "999999901"
    TEST_TG_ID_2 = "999999902"
    TEST_TG_ID_3 = "999999903"
    created_user_ids = []

    print("=" * 60)
    print("GUEST + BUSINESS FLOW TEST (non-destructive, live data)")
    print("=" * 60)

    async with async_session() as session:
        # --- Setup ---
        event_result = await session.execute(
            select(Event).order_by(Event.created_at.desc()).limit(1)
        )
        event = event_result.scalars().first()
        if not event:
            print("ERROR: No event found")
            return 1
        print(f"\nEvent: {event.name} (id={event.id})")

        role_result = await session.execute(select(Role).where(Role.code == "guest"))
        guest_role = role_result.scalars().first()
        if not guest_role:
            print("ERROR: No guest role found")
            return 1

        # Check tag state
        tag_result = await session.execute(text(
            "SELECT name, count(*) FROM tags t "
            "JOIN project_tags pt ON pt.tag_id = t.id "
            "GROUP BY t.name ORDER BY count(*) DESC"
        ))
        tags = tag_result.all()
        print(f"\n[TAGS] {len(tags)} tags in DB:")
        for name, cnt in tags:
            print(f"  {name}: {cnt} projects")

        project_count = (await session.execute(text(
            "SELECT count(*) FROM projects WHERE event_id = :eid"
        ), {"eid": event.id})).scalar()
        tagged_count = (await session.execute(text(
            "SELECT count(DISTINCT pt.project_id) FROM project_tags pt "
            "JOIN projects p ON p.id = pt.project_id WHERE p.event_id = :eid"
        ), {"eid": event.id})).scalar()
        print(f"\n[COVERAGE] {tagged_count}/{project_count} projects have tags")

        # ============================================================
        # TEST 1: Guest with tags (NLP + FinTech) — classic IDF path
        # ============================================================
        print("\n" + "=" * 60)
        print("TEST 1: Guest with tags (NLP, FinTech)")
        print("=" * 60)

        user1 = User(
            telegram_user_id=TEST_TG_ID,
            username="test_guest_flow_1",
            full_name="Тест Гостевой 1",
        )
        session.add(user1)
        await session.commit()
        await session.refresh(user1)
        created_user_ids.append(user1.id)

        ur1 = UserRole(user_id=user1.id, role_id=guest_role.id, event_id=event.id)
        session.add(ur1)
        await session.commit()

        profile1 = await profiling_service.get_or_create_profile(session, user1.id, event.id)
        await profiling_service.save_profile(
            session, profile1,
            selected_tags=["NLP", "FinTech"],
            keywords=["антифрод", "чат-бот"],
            raw_text="Интересуюсь антифродом в финтехе и чат-ботами",
        )
        await session.commit()
        print(f"  Profile: tags={profile1.selected_tags}, keywords={profile1.keywords}")

        print("  Generating recommendations...")
        recs1 = await profiling_service.generate_recommendations(session, profile1)

        if not recs1:
            print("  ERROR: No recommendations generated!")
            return 1

        print(f"  Total: {recs1['total']} recommendations")
        print(f"  Must visit: {len(recs1.get('must_visit', []))}")
        print(f"  If time: {len(recs1.get('if_time', []))}")

        print("\n  Must-visit projects:")
        for rec in recs1.get("must_visit", []):
            score = rec["relevance_score"]
            score_ok = "OK" if 0 <= score <= 100 else f"BAD ({score})"
            print(f"    #{rec['rank']} [{score_ok} score={score}] {rec['title'][:50]}")
            print(f"       tags={rec['tags']}, room={rec.get('room_number', 'n/a')}")

        print("\n  If-time projects:")
        for rec in recs1.get("if_time", []):
            score = rec["relevance_score"]
            score_ok = "OK" if 0 <= score <= 100 else f"BAD ({score})"
            print(f"    #{rec['rank']} [{score_ok} score={score}] {rec['title'][:50]}")

        # Verify scores are 0-100
        all_scores = [r["relevance_score"] for r in recs1.get("must_visit", []) + recs1.get("if_time", [])]
        bad_scores = [s for s in all_scores if s < 0 or s > 100]
        if bad_scores:
            print(f"\n  FAIL: Scores out of 0-100 range: {bad_scores}")
        else:
            print(f"\n  PASS: All {len(all_scores)} scores in 0-100 range")

        # Test project detail
        if recs1.get("must_visit"):
            first_rec = recs1["must_visit"][0]
            detail = await profiling_service.get_project_detail(
                session, profile1.id, uuid.UUID(first_rec["project_id"])
            )
            if detail:
                score_pct = min(int(detail["relevance_score"]), 100) if detail["relevance_score"] > 0 else 0
                print(f"\n  Detail card for #{first_rec['rank']}:")
                print(f"    Title: {detail['title'][:50]}")
                print(f"    Score display: {score_pct}%")
                print(f"    Tags: {detail['tags']}")
                print(f"    Summary: {(detail.get('llm_summary') or '')[:100]}...")
            else:
                print("  FAIL: Could not load project detail")

        # ============================================================
        # TEST 2: Guest with ONLY keywords, no tags — text search path
        # ============================================================
        print("\n" + "=" * 60)
        print("TEST 2: Guest with keywords only (no tags) — text search")
        print("=" * 60)

        user2 = User(
            telegram_user_id=TEST_TG_ID_2,
            username="test_guest_flow_2",
            full_name="Тест Гостевой 2",
        )
        session.add(user2)
        await session.commit()
        await session.refresh(user2)
        created_user_ids.append(user2.id)

        ur2 = UserRole(user_id=user2.id, role_id=guest_role.id, event_id=event.id)
        session.add(ur2)
        await session.commit()

        profile2 = await profiling_service.get_or_create_profile(session, user2.id, event.id)
        await profiling_service.save_profile(
            session, profile2,
            selected_tags=[],  # NO tags
            keywords=["антифрод", "fraud detection"],
            raw_text="Ищу проекты про антифрод и fraud detection в банковской сфере",
        )
        await session.commit()
        print(f"  Profile: tags=[], keywords={profile2.keywords}")

        print("  Generating recommendations (text-only)...")
        recs2 = await profiling_service.generate_recommendations(session, profile2)

        if recs2 and recs2["total"] > 0:
            print(f"  PASS: Text search found {recs2['total']} projects without tags!")
            for rec in recs2.get("must_visit", [])[:3]:
                print(f"    #{rec['rank']} [score={rec['relevance_score']}] {rec['title'][:50]}")
        else:
            print("  INFO: Text search returned 0 results (may be expected if no FTS matches)")

        # ============================================================
        # TEST 3: Skip-double-profiling check
        # ============================================================
        print("\n" + "=" * 60)
        print("TEST 3: Profile with tags → skip check")
        print("=" * 60)

        # Profile1 has tags → start_profiling should skip to GENERATE_PROGRAM
        async with async_session() as s2:
            p = await profiling_service.get_or_create_profile(s2, user1.id, event.id)
            if p.selected_tags:
                print(f"  PASS: Profile has tags={p.selected_tags} → would skip to generate")
            else:
                print("  FAIL: Profile has no tags, would not skip")

        # ============================================================
        # TEST 4: Business partner with extra_data (company + objectives)
        # ============================================================
        print("\n" + "=" * 60)
        print("TEST 4: Business partner with extra_data")
        print("=" * 60)

        biz_role_result = await session.execute(select(Role).where(Role.code == "business"))
        biz_role = biz_role_result.scalars().first()
        if not biz_role:
            print("  SKIP: No business role in DB")
        else:
            user3 = User(
                telegram_user_id=TEST_TG_ID_3,
                username="test_biz_partner_1",
                full_name="Тест Партнёр 1",
            )
            session.add(user3)
            await session.commit()
            await session.refresh(user3)
            created_user_ids.append(user3.id)

            ur3 = UserRole(user_id=user3.id, role_id=biz_role.id, event_id=event.id)
            session.add(ur3)
            await session.commit()

            profile3 = await profiling_service.get_or_create_profile(session, user3.id, event.id)
            await profiling_service.save_profile(
                session, profile3,
                selected_tags=["EdTech", "LLM"],
                keywords=["обучение", "адаптивные тесты", "LLM в образовании"],
                raw_text="Ищем AI-решения для корпоративного обучения, адаптивное тестирование",
                extra_data={
                    "company": "EduCorp",
                    "position": "CTO",
                    "partner_status": "Технологический партнёр",
                    "business_objectives": ["Найти технологического партнёра", "Интеграция AI в LMS"],
                },
            )
            await session.commit()
            print(f"  Profile: tags={profile3.selected_tags}, keywords={profile3.keywords}")
            print(f"  Extra: company={profile3.extra_data.get('company')}, "
                  f"objectives={profile3.extra_data.get('business_objectives')}")

            print("  Generating recommendations (with business context)...")
            recs3 = await profiling_service.generate_recommendations(session, profile3)

            if not recs3:
                print("  FAIL: No recommendations for business partner!")
            else:
                print(f"  Total: {recs3['total']} recommendations")
                print(f"  Must visit: {len(recs3.get('must_visit', []))}")
                print(f"  If time: {len(recs3.get('if_time', []))}")

                print("\n  Must-visit projects:")
                for rec in recs3.get("must_visit", []):
                    score = rec["relevance_score"]
                    score_ok = "OK" if 0 <= score <= 100 else f"BAD ({score})"
                    print(f"    #{rec['rank']} [{score_ok} score={score}] {rec['title'][:50]}")
                    print(f"       tags={rec['tags']}")

                all_scores = [r["relevance_score"] for r in
                              recs3.get("must_visit", []) + recs3.get("if_time", [])]
                bad_scores = [s for s in all_scores if s < 0 or s > 100]
                if bad_scores:
                    print(f"\n  FAIL: Scores out of 0-100 range: {bad_scores}")
                else:
                    print(f"\n  PASS: All {len(all_scores)} scores in 0-100 range")

                # Check that LLM summary mentions business context
                if recs3.get("must_visit"):
                    first_rec = recs3["must_visit"][0]
                    detail = await profiling_service.get_project_detail(
                        session, profile3.id, uuid.UUID(first_rec["project_id"])
                    )
                    if detail:
                        summary = detail.get("llm_summary") or ""
                        print(f"\n  Detail card for #{first_rec['rank']}:")
                        print(f"    Title: {detail['title'][:50]}")
                        print(f"    Score: {min(int(detail['relevance_score']), 100)}%")
                        print(f"    Summary: {summary[:150]}...")
                        # Check if business context influenced the summary
                        biz_keywords = ["educorp", "обучен", "lms", "корпоратив", "партнёр",
                                        "образован", "edtech", "адаптив"]
                        found_biz = [k for k in biz_keywords if k.lower() in summary.lower()]
                        if found_biz:
                            print(f"    PASS: Summary references business context: {found_biz}")
                        else:
                            print("    INFO: Summary doesn't explicitly mention business keywords "
                                  "(may still be contextually relevant)")

        # ============================================================
        # Cleanup
        # ============================================================
        print("\n" + "=" * 60)
        print("CLEANUP")
        print("=" * 60)

        for uid in created_user_ids:
            await session.execute(delete(Recommendation).where(
                Recommendation.guest_profile_id.in_(
                    select(GuestProfile.id).where(GuestProfile.user_id == uid)
                )
            ))
            await session.execute(delete(GuestProfile).where(GuestProfile.user_id == uid))
            await session.execute(delete(UserRole).where(UserRole.user_id == uid))
            await session.execute(delete(User).where(User.id == uid))
        await session.commit()
        print(f"  Cleaned up {len(created_user_ids)} test users")

        print("\n" + "=" * 60)
        print("ALL FLOW TESTS COMPLETE")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
