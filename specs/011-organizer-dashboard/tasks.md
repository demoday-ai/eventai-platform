# Tasks: Organizer Dashboard (EPIC-011)

**Input**: Design documents from `/specs/011-organizer-dashboard/`
**Prerequisites**: plan.md (required), spec.md (required)
**Dependencies**: EPIC-003, EPIC-006

## Phase 1: Dashboard Service

- [X] T001 Create dashboard_service.py with `get_student_stats(session, event_id)` function
- [X] T002 Implement `get_expert_stats(session, event_id)` for expert coverage
- [X] T003 Implement `get_guest_stats(session, event_id)` for guest breakdown
- [X] T004 Implement `get_alerts(student_stats, expert_stats)` for critical issues
- [X] T005 Implement `get_no_show_list(session, event_id)` for detailed no-shows
- [X] T006 Implement `get_problem_rooms(session, event_id)` for rooms without experts

**Checkpoint**: All stats functions work. ✓

---

## Phase 2: Bot Handler

- [X] T007 Create dashboard.py handler with `/dashboard` command
- [X] T008 Implement organizer-only access check
- [X] T009 Format dashboard message with all stats
- [X] T010 Add action buttons (refresh, noshows, problems, guests)
- [X] T011 Implement `dash:refresh` callback
- [X] T012 Implement `dash:noshows` callback with student list
- [X] T013 Implement `dash:problems` callback with room details
- [X] T014 Implement `dash:guests` callback with type breakdown
- [X] T015 Register handlers in app.py

**Checkpoint**: /dashboard command works with all callbacks. ✓

---

## Phase 3: Polish

- [X] T016 Format alerts with emoji indicators
- [X] T017 Handle empty data gracefully
- [X] T018 Add logging for dashboard access
- [X] T019 Update tasks.md marking completed

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3

**STATUS: COMPLETE** ✅
