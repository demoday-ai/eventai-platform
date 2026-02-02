# Tasks: Ознакомление студентов с расписанием (EPIC-003)

**Input**: Design documents from `/specs/003-student-confirmation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, quickstart.md

**Tests**: Not explicitly requested — test tasks omitted.

**Organization**: Tasks grouped by user story. US1+US2 are both P1 and tightly coupled (broadcast sends message → student acknowledges), so US2 is a continuation of US1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: New model, schema, migration for ParticipationRequest

- [ ] T001 Create ParticipationRequest model with ParticipationStatus enum in backend/app/models/participation.py
- [ ] T002 Register ParticipationRequest model in backend/app/models/__init__.py
- [ ] T003 Create Alembic migration 005_participation_requests.py in backend/alembic/versions/005_participation_requests.py
- [ ] T004 [P] Create Pydantic schemas (BroadcastResult, ParticipationSummary, UnacknowledgedStudent, ParticipationRequestDetail) in backend/app/schemas/participation.py
- [ ] T005 [P] Add acknowledgment inline keyboard function in backend/app/bot/keyboards.py

**Checkpoint**: Model + migration + schemas ready. Database can be migrated.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core service with shared logic used by all user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create participation_service.py with helper functions: match_project_to_user (project.telegram_contact → user.telegram_user_id), get_approved_clustering_run, build_slot_message in backend/app/services/participation_service.py
- [ ] T007 Add participation API router skeleton (empty endpoints) and register in backend/app/main.py, backend/app/api/participation.py

**Checkpoint**: Foundation ready — service file exists, router registered, helpers available.

---

## Phase 3: User Story 1 — Рассылка персональных слотов (Priority: P1) 🎯 MVP

**Goal**: Организатор запускает рассылку → каждый студент с Telegram-контактом получает персональное сообщение со слотом и кнопкой "Ознакомлен". Неподключённые студенты видны организатору.

**Independent Test**: Создать событие с расписанием, запустить /broadcast, проверить что студенты получили сообщения с корректными слотами.

### Implementation for User Story 1

- [ ] T008 [US1] Implement broadcast_slots function in participation_service: iterate approved room_projects, match to users, create ParticipationRequests, send Telegram messages with rate limiting (asyncio.sleep 0.04), collect unregistered list in backend/app/services/participation_service.py
- [ ] T009 [US1] Implement idempotent re-broadcast logic: skip unchanged slots, reset status and send "Расписание изменено" for changed slots in backend/app/services/participation_service.py
- [ ] T010 [US1] Implement POST /api/v1/participation/broadcast endpoint (organizer-only, calls broadcast_slots, returns BroadcastResult) in backend/app/api/participation.py
- [ ] T011 [US1] Implement /broadcast bot command handler for organizer: check approved clustering exists, call broadcast_slots, report results in backend/app/bot/handlers/confirmation.py
- [ ] T012 [US1] Register confirmation handler in bot application setup in backend/app/bot/app.py

**Checkpoint**: Organizer can /broadcast → students receive slot messages with "Ознакомлен" button. Re-broadcast is idempotent.

---

## Phase 4: User Story 2 — Подтверждение ознакомления студентом (Priority: P1)

**Goal**: Студент нажимает "Ознакомлен" → статус обновляется, бот подтверждает. Повторное нажатие сообщает что уже ознакомлен.

**Independent Test**: Отправить студенту сообщение с кнопкой, нажать "Ознакомлен", проверить что статус = acknowledged и бот ответил.

### Implementation for User Story 2

- [ ] T013 [US2] Implement acknowledge_participation function in participation_service: find request by short UUID, verify user, set status=acknowledged, set acknowledged_at in backend/app/services/participation_service.py
- [ ] T014 [US2] Implement callback handler for "ack:{id}" button: call acknowledge_participation, answer callback query with confirmation or "already acknowledged" in backend/app/bot/handlers/confirmation.py

**Checkpoint**: Student presses "Ознакомлен" → status updated, confirmation shown. MVP complete (US1 + US2).

---

## Phase 5: User Story 3 — Эскалация неознакомленных студентов (Priority: P2)

**Goal**: Автоматическое напоминание за 5 дней до DD, эскалация организатору за 2 дня. Периодическая проверка каждый час.

**Independent Test**: Создать студента со status=sent, установить event.start_date через 4 дня, запустить periodic task, проверить что студент получил напоминание.

### Implementation for User Story 3

- [ ] T015 [US3] Implement send_reminders function in participation_service: query unacknowledged requests where DD-5d, send reminder message, set reminder_sent_at in backend/app/services/participation_service.py
- [ ] T016 [US3] Implement escalate_to_organizers function in participation_service: query unacknowledged where DD-2d, send alert to organizer telegram IDs with student list in backend/app/services/participation_service.py
- [ ] T017 [US3] Implement periodic_check_task async function: run every hour, call send_reminders + escalate_to_organizers + daily_summary, register in FastAPI lifespan in backend/app/services/participation_service.py
- [ ] T018 [US3] Register periodic task in FastAPI lifespan (asyncio.create_task) in backend/app/main.py

**Checkpoint**: Automatic reminders and escalation work on schedule relative to DD date.

---

## Phase 6: User Story 4 — Дашборд ознакомлений для организатора (Priority: P2)

**Goal**: Организатор видит сводку (ознакомились / не ответили) с разбивкой по залам. Может запросить список неознакомленных. Ежедневная автосводка.

**Independent Test**: Создать набор студентов с разными статусами, запросить /status, проверить корректность сводки.

### Implementation for User Story 4

- [ ] T019 [P] [US4] Implement get_participation_summary function in participation_service: aggregate counts by status and room, return ParticipationSummary in backend/app/services/participation_service.py
- [ ] T020 [P] [US4] Implement get_unacknowledged_list function in participation_service: query sent requests with project/room details, return list of UnacknowledgedStudent in backend/app/services/participation_service.py
- [ ] T021 [US4] Implement GET /api/v1/participation/summary endpoint (organizer-only, optional room_id filter) in backend/app/api/participation.py
- [ ] T022 [US4] Implement GET /api/v1/participation/unacknowledged endpoint (organizer-only, optional room_id filter) in backend/app/api/participation.py
- [ ] T023 [US4] Implement /status bot command handler: show summary with per-room inline buttons, drill-down to unacknowledged list in backend/app/bot/handlers/confirmation.py
- [ ] T024 [US4] Implement daily_summary function in participation_service: format summary text, send to all organizer telegram IDs (called by periodic task from T017) in backend/app/services/participation_service.py

**Checkpoint**: Organizer can /status, sees summary, drills into rooms, gets daily auto-summary.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, error handling, final integration

- [ ] T025 Handle Telegram API errors in broadcast: 403 Forbidden (bot blocked), 400 Bad Request (invalid chat_id) → add to unregistered list in backend/app/services/participation_service.py
- [ ] T026 Add message frequency guard: track messages sent per student, enforce ≤4 messages per cycle in backend/app/services/participation_service.py
- [ ] T027 [P] Add participation request detail endpoint GET /api/v1/participation/{request_id} in backend/app/api/participation.py
- [ ] T028 Run quickstart.md scenarios validation: test all 6 integration scenarios end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (model + schema must exist)
- **US1 (Phase 3)**: Depends on Phase 2 — broadcast logic needs service + helpers
- **US2 (Phase 4)**: Depends on Phase 3 — acknowledgment needs broadcast to have sent messages
- **US3 (Phase 5)**: Depends on Phase 2 — can start in parallel with US1/US2 (but needs sent messages to test)
- **US4 (Phase 6)**: Depends on Phase 2 — can start in parallel with US1/US2
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only. Core MVP.
- **US2 (P1)**: Depends on US1 (student needs to receive message before acknowledging)
- **US3 (P2)**: Depends on Foundational. Can be developed alongside US1/US2. Needs sent messages to test.
- **US4 (P2)**: Depends on Foundational. Can be developed alongside US1/US2. Summary logic is independent.

### Within Each User Story

- Service functions before endpoints/handlers
- Bot handlers after API endpoints (shared service layer)
- Periodic tasks after core logic

### Parallel Opportunities

- T004 + T005 can run in parallel with T001-T003 (different files)
- T019 + T020 can run in parallel (different functions, same file but independent)
- US3 + US4 can be developed in parallel after US1+US2 complete
- T025 + T026 + T027 can run in parallel (different concerns)

---

## Parallel Example: Phase 1 Setup

```bash
# These can run in parallel (different files):
Task T001: "Create ParticipationRequest model in backend/app/models/participation.py"
Task T004: "Create Pydantic schemas in backend/app/schemas/participation.py"
Task T005: "Add keyboard function in backend/app/bot/keyboards.py"
```

## Parallel Example: Phase 6

```bash
# These can run in parallel (independent functions):
Task T019: "get_participation_summary in participation_service.py"
Task T020: "get_unacknowledged_list in participation_service.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup (model, migration, schemas)
2. Complete Phase 2: Foundational (service skeleton, router)
3. Complete Phase 3: US1 — Broadcast slots
4. Complete Phase 4: US2 — Student acknowledgment
5. **STOP and VALIDATE**: Test broadcast + acknowledgment flow end-to-end
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 + US2 → Broadcast + Acknowledgment (MVP!) → Test → Deploy
3. US3 → Automatic reminders + escalation → Test → Deploy
4. US4 → Organizer dashboard + daily summary → Test → Deploy
5. Polish → Error handling, frequency guard, edge cases

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- US1 and US2 are both P1 but sequential: broadcast must happen before acknowledgment
- US3 and US4 are both P2 and can be developed in parallel
- All service logic concentrated in single file (participation_service.py) per existing pattern
- Bot handler in single file (confirmation.py) per existing pattern
- Migration number is 005 (after 004_guest_profiling)
