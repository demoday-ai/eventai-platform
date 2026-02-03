# Tasks: Expert Project Overview (EPIC-008)

**Input**: Design documents from `/specs/008-expert-project-overview/`
**Prerequisites**: plan.md (required), spec.md (required)
**Dependencies**: EPIC-002, EPIC-004, EPIC-007

## Phase 1: Setup & Data Model

- [X] T001 Create migration 008_expert_briefing.py with ExpertBriefing table
- [X] T002 Create ExpertBriefing model in backend/app/models/expert_briefing.py
- [X] T003 Export model in backend/app/models/__init__.py

**Checkpoint**: ExpertBriefing entity exists and migrated. ✓

---

## Phase 2: GitHub Service (US2)

- [X] T004 Create github_service.py with `get_repo_status(github_url)` function
- [X] T005 Implement async httpx call to GitHub API for last commit date
- [X] T006 Handle rate limit and timeout gracefully (return "unavailable" status)

**Checkpoint**: GitHub status can be fetched for any repo URL. ✓

---

## Phase 3: Briefing Service (US1)

- [X] T007 Create briefing_service.py with `get_room_projects(room_id)` function
- [X] T008 Implement `format_project_card(project, github_status)` — single card text
- [X] T009 Implement `format_briefing(expert, projects)` — full briefing message
- [X] T010 Implement message splitting for long briefings (4096 char limit)
- [X] T011 Implement `send_briefing(expert, bot)` — send to Telegram
- [X] T012 Implement `send_all_briefings(event_id, bot)` — batch send to all experts

**Checkpoint**: Briefings can be generated and sent to experts. ✓

---

## Phase 4: Bot Handler (FR-010)

- [X] T013 Create briefing.py handler with `/briefing` command
- [X] T014 Add organizer-only access check
- [X] T015 Show preview with expert count before send
- [X] T016 Add confirmation keyboard (send/cancel)
- [X] T017 Execute send and show delivery report
- [X] T018 Register handler in app.py

**Checkpoint**: Organizer can trigger briefing via /briefing command. ✓

---

## Phase 5: Scheduler Integration (FR-001)

- [X] T019 Add scheduled job for briefing 24h before DD in main.py
- [X] T020 Integrate with existing EPIC-007 scheduler infrastructure

**Checkpoint**: Briefings auto-send 24h before DD. ✓

---

## Phase 6: Polish & Edge Cases

- [X] T021 Handle expert without room (skip with warning log)
- [X] T022 Handle empty room (send "no projects" message)
- [X] T023 Add comprehensive logging for delivery tracking
- [X] T024 Update tasks.md marking completed tasks

---

## Dependencies & Execution Order

- Phase 1 → Phase 2, Phase 3 (parallel)
- Phase 2 + Phase 3 → Phase 4
- Phase 4 → Phase 5
- Phase 5 → Phase 6

**STATUS: COMPLETE** ✅
