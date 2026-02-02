# Tasks: Распределение экспертов (EPIC-004)

**Input**: Design documents from `/specs/004-expert-assignment/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User Stories 1-3 are P1, Stories 4-5 are P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/app/` (models, services, schemas, api, bot)
- **Migrations**: `backend/alembic/versions/`
- **Scripts**: `scripts/`
- **Seed data**: `data/seed/`

---

## Phase 1: Setup

**Purpose**: Dependencies, seed data preparation, database migration

- [x] T001 Add APScheduler dependency to `backend/pyproject.toml` (`apscheduler>=3.10`)
- [x] T002 Create seed preparation script `scripts/prepare_expert_seed.py` — merge `data/expert-mapping.json` + `data/experts-public.json` by `id` field → output `data/seed/experts_seed.json` (294 experts with: id, name, telegram, position, expertise_tags, dd_status, inviter). See research.md R4 for output format.
- [x] T003 Run `scripts/prepare_expert_seed.py` and verify `data/seed/experts_seed.json` is generated with 294 records, ~208 with tags, ~86 without.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database models, migration, schemas — MUST complete before ANY user story

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Create Expert model in `backend/app/models/expert.py` — fields: seed_id (VARCHAR 20, UNIQUE), name (VARCHAR 200), telegram_username (VARCHAR 100, nullable), position (VARCHAR 300, nullable), inviter (VARCHAR 100, nullable), dd_status_seed (VARCHAR 50, nullable), user_id (FK → users.id, nullable, UNIQUE), event_id (FK → events.id), bot_started (BOOLEAN, default false), bot_started_at (DateTime, nullable). Indexes on telegram_username and seed_id. Unique constraint on (seed_id, event_id). Relationships: tags (M2M via expert_tags), user (1:1 nullable), assignments (1:M).
- [x] T005 [P] Create ExpertTag model in `backend/app/models/expert_tag.py` — junction table: expert_id (FK → experts.id, CASCADE), tag_id (FK → tags.id, CASCADE). Unique constraint on (expert_id, tag_id).
- [x] T006 [P] Create ExpertRoomAssignment model in `backend/app/models/expert_room_assignment.py` — fields: expert_id (FK → experts.id, CASCADE), room_id (FK → rooms.id, CASCADE), clustering_run_id (FK → clustering_runs.id, CASCADE), match_score (FLOAT, default 0.0), is_manual (BOOLEAN, default false), status (VARCHAR 20, default 'proposed'), status_changed_at (DateTime, nullable), invite_viewed_at (DateTime, nullable), reminder_count (INTEGER, default 0), last_reminder_at (DateTime, nullable), updated_at (DateTime, nullable, onupdate). Unique constraint on (expert_id, clustering_run_id). Status enum: proposed, approved, invite_ready, invited, confirmed, declined, reassign_requested, no_show. Indexes on clustering_run_id, room_id, status.
- [x] T007 [P] Create Escalation model in `backend/app/models/escalation.py` — fields: expert_id (FK → experts.id, CASCADE), room_id (FK → rooms.id, CASCADE), event_id (FK → events.id, CASCADE), type (VARCHAR 30), message (TEXT), resolved (BOOLEAN, default false), resolved_at (DateTime, nullable). Indexes on event_id and resolved.
- [x] T008 Update `backend/app/models/__init__.py` — add Expert, ExpertTag, ExpertRoomAssignment, Escalation to imports and __all__.
- [x] T009 Create Alembic migration `backend/alembic/versions/003_expert_assignment.py` — depends on 001_initial_schema and 002_projects_clustering. Creates 4 tables in order: experts → expert_tags → expert_room_assignments → escalations. Include all indexes from data-model.md.
- [x] T010 [P] Create Pydantic schemas in `backend/app/schemas/expert.py` — ExpertUploadRow, ExpertUploadResult, ReplaceConfirmation, ExpertResponse, ExpertDetailResponse, MatchingRequest, MatchingResult, RoomMatchSummary, AssignmentResponse, MoveExpertRequest, ApproveResult, InvitePreview, InviteConfirmResult, CoverageDashboard, RoomCoverageSummary, RoomCoverageDetail, EscalationResponse. All per contracts/api.yaml.
- [x] T011 Create expert_service.py in `backend/app/services/expert_service.py` — functions: load_seed_experts(session, event_id, seed_path) — parse experts_seed.json, resolve tags via existing tags table, create Expert + ExpertTag records, skip if experts already exist for event. get_experts(session, event_id, filters) — list experts with eager-loaded tags and latest assignment. get_expert_by_telegram(session, event_id, username) — lookup by telegram_username (case-insensitive). upload_experts(session, event_id, file) — parse CSV/JSON upload, validate rows, replace if confirmed. delete_all_experts(session, event_id) — for replace flow.
- [x] T012 Update `backend/app/main.py` — add expert seed loading in lifespan startup (after project seed loading): call load_seed_experts if no experts exist for current event.

**Checkpoint**: Foundation ready — all models, migration, schemas, and seed loading in place.

---

## Phase 3: User Story 1 — Автоматический матчинг экспертов по комнатам (Priority: P1) MVP

**Goal**: Organizer runs matching, sees weighted tag-overlap distribution, can manually adjust and approve.

**Independent Test**: Load 294 experts from seed + approved clustering with rooms. Run matching. Verify: NLP expert → NLP room, Security expert → Security room. Move an expert manually. Approve distribution.

**Requires**: Approved clustering run (EPIC-002). If none exists — error message.

### Implementation for User Story 1

- [x] T013 [US1] Create matching_service.py in `backend/app/services/matching_service.py` — core matching algorithm per research.md R1-R3:
  1. `get_room_tags(session, clustering_run_id)` — for each room, compute tag set as union of project tags via room_projects → projects → project_tags → tags.
  2. `compute_idf_weights(session, event_id)` — IDF weights: log(total_experts / experts_with_tag) for each tag.
  3. `resolve_adjacent_tags(tags: list[str])` — single LLM call via existing llm_client to get adjacency pairs. Fallback: empty adjacency if LLM unavailable.
  4. `run_matching(session, event_id)` — fetch approved clustering, compute room tags, IDF weights, adjacent tags. For each expert with tags: score = sum(idf * match_factor) per room. Assign to highest-scoring room (tie-break: least-covered room). Create ExpertRoomAssignment records with status='proposed'. Return MatchingResult.
  5. `move_expert(session, assignment_id, target_room_id)` — update room_id, set is_manual=true, recalc match_score.
  6. `approve_matching(session, clustering_run_id)` — update all proposed → approved.
  7. `get_current_matching(session, event_id)` — return latest assignments grouped by room.
- [x] T014 [US1] Create API endpoints in `backend/app/api/experts.py`:
  - POST `/experts/upload` (multipart, organizer-only) — calls expert_service.upload_experts
  - GET `/experts` — calls expert_service.get_experts with query filters (has_tags, tag, search)
  - GET `/experts/{expert_id}` — calls expert_service.get_expert_detail
  - POST `/matching/run` (organizer-only) — calls matching_service.run_matching
  - GET `/matching/current` — calls matching_service.get_current_matching
  - POST `/matching/{assignment_id}/move` (organizer-only) — calls matching_service.move_expert
  - POST `/matching/approve` (organizer-only) — calls matching_service.approve_matching
- [x] T015 [US1] Register experts router in `backend/app/main.py` — add `app.include_router(experts_router, prefix="/api/v1")`.
- [x] T016 [US1] Create bot keyboards for expert assignment in `backend/app/bot/keyboards.py` — add keyboards: expert_management_menu (Запустить матчинг, Загрузить экспертов, Покрытие, Эскалации), matching_result_rooms (list rooms with expert counts, paginated), room_expert_detail (expert list with scores, Перенести button), move_target_room (list of rooms to move to), approve_matching_confirm (Утвердить / Перезапустить).
- [x] T017 [US1] Create bot handler for organizer matching wizard in `backend/app/bot/handlers/expert_assignment.py` — ConversationHandler states: MENU → RUN_MATCHING → VIEW_RESULT → ROOM_DETAIL → MOVE_SELECT_EXPERT → MOVE_SELECT_ROOM → APPROVE_CONFIRM. Entry point: `/experts` command (organizer only). Calls matching_service functions. Shows matching results per room with pagination. Supports manual move flow. Approve flow with confirmation.
- [x] T018 [US1] Register expert_assignment handler in `backend/app/bot/app.py` — import and add ConversationHandler to application.

**Checkpoint**: US1 complete — organizer can run matching, view/adjust results, approve distribution.

---

## Phase 4: User Story 2 — Персональное приглашение эксперта (Priority: P1)

**Goal**: After approved distribution, organizer confirms invite sending. Experts come via bot link, see personalized invite, respond with Иду/Другая комната/Не смогу.

**Independent Test**: Approve a distribution. Confirm invite sending. Simulate expert `/start expert` in bot. Verify personalized message with room + tags. Click "Иду" → status confirmed. Click "Хочу другую комнату" → see room list.

**Depends on**: US1 (approved matching must exist)

### Implementation for User Story 2

- [x] T019 [US2] Create invite_service.py in `backend/app/services/invite_service.py` — functions:
  1. `get_invite_preview(session, event_id)` — count experts with/without telegram, generate sample message, build bot link.
  2. `confirm_invites(session, event_id)` — update all approved assignments → invite_ready. Return bot link and count.
  3. `handle_expert_start(session, event_id, telegram_username)` — find expert by username (case-insensitive), mark bot_started=true, set bot_started_at. If assignment status=invite_ready → update to invited, set invite_viewed_at. Return expert + assignment info or None.
  4. `confirm_attendance(session, assignment_id)` — set status=confirmed, status_changed_at.
  5. `decline_attendance(session, assignment_id)` — set status=declined, status_changed_at.
  6. `request_reassignment(session, assignment_id)` — set status=reassign_requested. Return list of alternative rooms.
  7. `reassign_expert(session, assignment_id, new_room_id)` — update room_id, set is_manual=true, status=confirmed.
  8. `get_experts_without_telegram(session, event_id)` — list experts without telegram_username (FR-010).
- [x] T020 [US2] Add invite API endpoints to `backend/app/api/experts.py`:
  - GET `/invites/preview` (organizer-only) — calls invite_service.get_invite_preview
  - POST `/invites/confirm` (organizer-only) — calls invite_service.confirm_invites
- [x] T021 [US2] Add invite keyboards in `backend/app/bot/keyboards.py` — invite_preview (Подтвердить рассылку / Отмена), expert_invite_actions (Иду / Хочу другую комнату / Не смогу), alternative_rooms (list of rooms with themes, paginated), expert_confirmed (acknowledgment).
- [x] T022 [US2] Add invite sending flow to organizer wizard in `backend/app/bot/handlers/expert_assignment.py` — new states: INVITE_PREVIEW → INVITE_CONFIRM. After approve, add button "Отправить приглашения". Show preview (count, sample). On confirm → call invite_service.confirm_invites → show bot link for sharing.
- [x] T023 [US2] Add expert /start handler in `backend/app/bot/handlers/expert_assignment.py` — hook into existing /start flow: if args='expert', call invite_service.handle_expert_start(username). If found: show personalized invite with room, tags, project count + action buttons. If not found: "Вы не в списке экспертов." Handle callbacks: invite_confirm → confirm_attendance, invite_decline → decline_attendance, invite_reassign → show room list → reassign_expert.
- [x] T024 [US2] Update existing `/start` handler in `backend/app/bot/handlers/start.py` — if command args contain 'expert', delegate to expert_assignment handler instead of normal onboarding flow.

**Checkpoint**: US2 complete — full invite flow: organizer previews/confirms, experts respond via bot link.

---

## Phase 5: User Story 3 — Дашборд покрытия для организатора (Priority: P1)

**Goal**: Organizer sees per-room coverage dashboard with color indicators, drill-down to expert lists, suggested adjacent experts for uncovered rooms.

**Independent Test**: Create rooms with varied expert confirmations (2+ confirmed, 1 confirmed, 0 confirmed). View dashboard. Verify color indicators, counts, and drill-down.

**Depends on**: US1 (assignments exist), US2 (some experts have responded)

### Implementation for User Story 3

- [x] T025 [US3] Add coverage functions to `backend/app/services/invite_service.py`:
  1. `get_coverage_dashboard(session, event_id)` — per room: count confirmed, declined, no_response, not_in_bot. Determine coverage_level (covered/partial/uncovered). Compute totals. Return CoverageDashboard schema.
  2. `get_room_coverage_detail(session, event_id, room_id)` — list experts for room with statuses. Query adjacent-tag experts not assigned to this room as suggestions.
- [x] T026 [US3] Add coverage API endpoints to `backend/app/api/experts.py`:
  - GET `/coverage` — calls invite_service.get_coverage_dashboard
  - GET `/coverage/{room_id}` — calls invite_service.get_room_coverage_detail
- [x] T027 [US3] Add coverage keyboards in `backend/app/bot/keyboards.py` — coverage_dashboard_rooms (list rooms as buttons with emoji indicators: green/yellow/red), coverage_room_detail (expert list with statuses, "Назад" button).
- [x] T028 [US3] Add coverage flow to organizer wizard in `backend/app/bot/handlers/expert_assignment.py` — new states: COVERAGE_DASHBOARD → COVERAGE_ROOM_DETAIL. Entry from main menu "Покрытие" button. Format dashboard as text message with emoji per research.md R6 format. Room buttons for drill-down. Show suggested adjacent experts for uncovered rooms.

**Checkpoint**: US3 complete — organizer has full visibility into expert coverage per room.

---

## Phase 6: User Story 5 — Эскалация и напоминания (Priority: P2)

**Goal**: Automated reminders to non-responding experts (3 days), escalation alerts to organizer (5 days / 2 days before DD). Max 4 messages per expert.

**Independent Test**: Create expert with invite_viewed 4+ days ago, no response. Trigger scheduler check. Verify reminder sent (if in bot) or escalation created (if not in bot or 5+ days).

**Note**: User Story 4 (time slots) is deferred — P2 with lower priority than escalation which is critical for DD coverage.

### Implementation for User Story 5

- [x] T029 [US5] Add reminder/escalation functions to `backend/app/services/invite_service.py`:
  1. `check_and_send_reminders(session, event_id, bot)` — find experts with status=invited, invite_viewed_at > 3 days ago, reminder_count < 4, bot_started=true. Send reminder message via bot. Increment reminder_count, set last_reminder_at. Create escalation record type=no_response_reminder.
  2. `check_and_escalate(session, event_id, bot, dd_date)` — find experts not responded after 5 days OR 2 days before DD. Create escalation records type=no_response_escalation. Check rooms with 0 confirmed → type=room_uncovered. Check rooms with 1 confirmed → type=room_partially_covered. Send summary alert to organizer via bot.
  3. `resolve_escalation(session, escalation_id)` — set resolved=true, resolved_at.
  4. `get_escalations(session, event_id, resolved=False)` — list escalations with expert/room info.
- [x] T030 [US5] Add escalation API endpoints to `backend/app/api/experts.py`:
  - GET `/escalations` — calls invite_service.get_escalations
  - POST `/escalations/{escalation_id}/resolve` (organizer-only) — calls invite_service.resolve_escalation
- [x] T031 [US5] Setup APScheduler in `backend/app/main.py` — add AsyncIOScheduler in lifespan startup. Schedule two IntervalTrigger jobs (every 12 hours): check_and_send_reminders, check_and_escalate. Pass bot instance and session factory. Shutdown scheduler in lifespan shutdown.
- [x] T032 [US5] Add escalation keyboards in `backend/app/bot/keyboards.py` — escalation_list (list escalations as buttons, grouped by type), escalation_detail (Разрешить / Назад).
- [x] T033 [US5] Add escalation flow to organizer wizard in `backend/app/bot/handlers/expert_assignment.py` — new states: ESCALATION_LIST → ESCALATION_DETAIL. Entry from main menu "Эскалации" button. Show unresolved escalations grouped by type. Detail view with resolve button.

**Checkpoint**: US5 complete — automated reminder/escalation pipeline active.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration, edge cases, final wiring

- [x] T034 Add no-show marking to organizer flow in `backend/app/bot/handlers/expert_assignment.py` — in room detail view, add "No-show" button for confirmed experts. Update assignment status to no_show. Recalculate coverage.
- [x] T035 Add expert room change flow (FR-014) in `backend/app/bot/handlers/expert_assignment.py` — expert who already confirmed can request room change (before deadline). Show current room + alternatives. Update assignment on new selection.
- [x] T036 Validate all Python files with `python -m py_compile` — syntax check across all new files.
- [x] T037 Run quickstart.md validation — walk through the 8-step demo flow end-to-end, verify each step works.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on T001 (APScheduler dep) and T003 (seed data). BLOCKS all user stories.
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on US1 (needs approved matching)
- **Phase 5 (US3)**: Depends on US1 (needs assignments). Can parallelize with US2.
- **Phase 6 (US5)**: Depends on US2 (needs invite statuses and bot instance)
- **Phase 7 (Polish)**: Depends on all prior phases

### User Story Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundation)
                       │
                       ▼
                    Phase 3 (US1: Matching) ──────────────┐
                       │                                   │
                       ├──────────────┐                    │
                       ▼              ▼                    ▼
               Phase 4 (US2)    Phase 5 (US3)       [can parallel]
               (Invites)        (Coverage)
                       │              │
                       ▼              │
               Phase 6 (US5)  ◄───────┘
               (Escalation)
                       │
                       ▼
               Phase 7 (Polish)
```

### Within Each User Story

- Models → Services → API endpoints → Bot keyboards → Bot handler → Registration
- Services depend on models
- API endpoints depend on services + schemas
- Bot handler depends on services + keyboards

### Parallel Opportunities

**Phase 2**: T004, T005, T006, T007 (all models) can run in parallel. T010 (schemas) can parallel with models.
**Phase 3**: T016 (keyboards) can parallel with T013 (service) since they use different files.
**Phase 5 + Phase 4**: US3 (Coverage) can start as soon as US1 is done, in parallel with US2 (Invites).

---

## Parallel Example: Phase 2 (Foundational)

```text
# Launch all models in parallel:
Task T004: "Create Expert model in backend/app/models/expert.py"
Task T005: "Create ExpertTag model in backend/app/models/expert_tag.py"
Task T006: "Create ExpertRoomAssignment model in backend/app/models/expert_room_assignment.py"
Task T007: "Create Escalation model in backend/app/models/escalation.py"
Task T010: "Create Pydantic schemas in backend/app/schemas/expert.py"

# Then sequentially:
Task T008: "Update __init__.py" (depends on T004-T007)
Task T009: "Create migration" (depends on T004-T007)
Task T011: "Create expert_service.py" (depends on T004-T007, T010)
Task T012: "Update main.py seed loading" (depends on T011)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T012)
3. Complete Phase 3: User Story 1 — Matching (T013-T018)
4. **STOP and VALIDATE**: Run matching with 294 experts × approved clustering
5. Deploy/demo if ready — organizer can see AI-proposed distribution

### Incremental Delivery

1. Setup + Foundational → Foundation ready (T001-T012)
2. Add US1 (Matching) → Organizer runs/adjusts/approves matching (MVP!)
3. Add US2 (Invites) → Experts respond via bot link
4. Add US3 (Coverage) → Organizer monitors coverage dashboard
5. Add US5 (Escalation) → Automated reminders + alerts
6. Polish → No-show, room changes, validation

### Deferred (P2, not in this iteration)

- **User Story 4 (Time slots)**: Not included in tasks. Requires additional data model (time_slot table), UI for slot selection, time-based coverage view. Can be added post-MVP.

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 37 |
| Phase 1 (Setup) | 3 |
| Phase 2 (Foundation) | 9 |
| Phase 3 (US1 Matching) | 6 |
| Phase 4 (US2 Invites) | 6 |
| Phase 5 (US3 Coverage) | 4 |
| Phase 6 (US5 Escalation) | 5 |
| Phase 7 (Polish) | 4 |
| Parallel opportunities | 7 tasks in Phase 2, US3+US2 can parallel |
| MVP scope | Phases 1-3 (18 tasks) |
| Full scope | Phases 1-7 (37 tasks) |

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Story 4 (Time slots, P2) deferred — not critical for DD coverage
- User Story 5 (Escalation, P2) included — critical for reducing no-show
- All services async (SQLAlchemy 2.0 async sessions)
- Reuses existing llm_client.py for adjacent tag resolution
- Reuses existing tags table from EPIC-002
