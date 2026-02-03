# Tasks: Напоминания перед Demo Day (EPIC-007)

**Input**: Design documents from `/specs/007-dd-reminders/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api.yaml, quickstart.md

**Tests**: Not explicitly requested — manual validation via bot + quickstart.md scenarios.

**Key Context**: Extends existing reminder infrastructure (EPIC-003 participation_service, EPIC-004 invite_service). New tables `reminder_batches` and `notifications`. Bot command `/remind` with preview → confirm → send → report flow.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new files, Pydantic schemas, database migration

- [x] T001 [P] Create reminder models (ReminderBatch, Notification, enums) in `backend/app/models/reminder.py` per data-model.md
- [x] T002 [P] Create reminder Pydantic schemas in `backend/app/schemas/reminder.py` — ReminderPreview, RolePreview, ReminderBatchSummary, ReminderBatchDetail, NotificationSummary per contracts/api.yaml
- [x] T003 [P] Create empty `backend/app/services/reminder_service.py` with function stubs: `get_preview()`, `create_batch()`, `execute_batch()`, `check_duplicate()`, `get_student_recipients()`, `get_expert_recipients()`, `get_guest_recipients()`, `format_message()`
- [x] T004 [P] Create empty `backend/app/bot/handlers/reminder.py` with stub for `/remind` command handler
- [x] T005 Generate Alembic migration for reminder_batches + notifications tables + telegram_chat_id on experts: `alembic revision --autogenerate -m "add_reminder_tables"`
- [x] T006 Run migration: `alembic upgrade head`
- [x] T007 Register Reminder model in `backend/app/models/__init__.py`

**Checkpoint**: New files exist with stubs. Migration applied. No functionality yet.

---

## Phase 2: Foundational (Core Service Logic)

**Purpose**: Implement `reminder_service.py` — the core logic that ALL user stories depend on

**⚠️ CRITICAL**: Bot handler and all user stories depend on service being complete

- [x] T008 Implement `check_duplicate(session, event_id, reminder_type)` in `backend/app/services/reminder_service.py` — check ReminderBatch for same type within 24h, return batch info if found
- [x] T009 Implement `get_student_recipients(session, event_id)` in `backend/app/services/reminder_service.py` — query ParticipationRequest with room_project_id, return list with user data and acknowledgment status
- [x] T010 Implement `get_expert_recipients(session, event_id, clustering_id)` in `backend/app/services/reminder_service.py` — query ExpertRoomAssignment (not declined), return list with expert data and room info
- [x] T011 Implement `get_guest_recipients(session, event_id)` in `backend/app/services/reminder_service.py` — query User with guest_subtype, return list with program data if exists
- [x] T012 Implement `get_preview(session, event_id, reminder_type)` in `backend/app/services/reminder_service.py` — aggregate all recipients, count by role, detect skipped (no telegram), check duplicate
- [x] T013 Implement `create_batch(session, event_id, reminder_type, initiated_by, initiated_by_name)` in `backend/app/services/reminder_service.py` — create ReminderBatch with status=confirmed, return batch_id
- [x] T014 Add reminder keyboards in `backend/app/bot/keyboards.py` — `reminder_type_keyboard()` with За день/За час buttons, `reminder_preview_keyboard(batch_id)` with Отправить/Отмена buttons, `reminder_resend_keyboard(batch_id)` for duplicate confirmation

**Checkpoint**: Service layer complete with recipient queries and batch creation.

---

## Phase 3: User Story 4 — Организатор управляет рассылкой (Priority: P2) 🎯 MVP Entry Point

**Goal**: Организатор запускает рассылку командой `/remind`, видит превью по ролям, подтверждает, получает отчёт

**Why P2 first**: US4 is the entry point for ALL reminders. Without `/remind` command, no user story can be triggered. Must implement first despite lower priority in spec.

**Independent Test**: `/remind` → type selection → preview with counts → confirm → report (no actual send yet)

### Implementation for User Story 4

- [x] T015 [US4] Implement `/remind` command handler in `backend/app/bot/handlers/reminder.py` — check organizer access, check event exists, show type selection keyboard
- [x] T016 [US4] Implement type selection callback `rem:type:day` / `rem:type:hour` in `backend/app/bot/handlers/reminder.py` — call `get_preview()`, format preview message with counts per role, show confirm/cancel keyboard
- [x] T017 [US4] Implement duplicate warning flow in `backend/app/bot/handlers/reminder.py` — if `check_duplicate()` returns batch, show warning with resend/cancel options
- [x] T018 [US4] Implement confirm callback `rem:send:{batch_id}` in `backend/app/bot/handlers/reminder.py` — call `create_batch()`, call `execute_batch()`, update message with progress, show final report
- [x] T019 [US4] Implement cancel callback `rem:cancel` in `backend/app/bot/handlers/reminder.py` — edit message to "Рассылка отменена"
- [x] T020 [US4] Register reminder handlers in `backend/app/bot/app.py` — add CommandHandler for `/remind`, CallbackQueryHandlers for `rem:type:`, `rem:send:`, `rem:cancel`, `rem:resend:`
- [x] T021 [US4] Handle edge case: no event in 2 days — return "Нет события в ближайшие дни"
- [x] T022 [US4] Handle edge case: non-organizer — return "Команда доступна только организаторам"

**Checkpoint**: `/remind` command works for organizers. Shows preview, handles confirm/cancel. No actual message sending yet.

---

## Phase 4: User Story 1 — Напоминание «за день» студентам и экспертам (Priority: P1)

**Goal**: Студенты и эксперты получают персональные напоминания за день до DD с указанием зала

**Independent Test**: Запустить `/remind` → За день → Отправить. Проверить что студенты и эксперты получили сообщения с залами.

### Implementation for User Story 1

- [x] T023 [US1] Implement `format_student_day_before(participation, event)` in `backend/app/services/reminder_service.py` — format message with project, room, date. Add acknowledgment warning if status != ACKNOWLEDGED
- [x] T024 [US1] Implement `format_expert_day_before(assignment, project_count)` in `backend/app/services/reminder_service.py` — format message with room, project count
- [x] T025 [US1] Implement `send_student_reminders(session, batch_id, bot)` in `backend/app/services/reminder_service.py` — iterate students, send messages with 0.04s delay, create Notification records, update sent/failed counts
- [x] T026 [US1] Implement `send_expert_reminders(session, batch_id, bot)` in `backend/app/services/reminder_service.py` — iterate experts with telegram_chat_id, send messages with delay, create Notification records
- [x] T027 [US1] Update `execute_batch()` in `backend/app/services/reminder_service.py` — call send_student_reminders + send_expert_reminders for day_before type
- [x] T028 [US1] Handle unacknowledged students — add "Пожалуйста, подтвердите участие" with Ознакомлен button to message
- [x] T029 [US1] Handle declined experts — exclude from recipient list, count in preview as "отклонили"

**Checkpoint**: Day-before reminders work for students and experts with personalized messages.

---

## Phase 5: User Story 2 — Напоминание «за день» гостям и бизнес-партнёрам (Priority: P1)

**Goal**: Гости и бизнес-партнёры получают напоминание с их персональной программой (топ-проекты)

**Independent Test**: Создать гостя с программой, запустить напоминания "за день" — проверить что получил сообщение с проектами

### Implementation for User Story 2

- [x] T030 [US2] Implement `get_guest_program(session, user_id)` in `backend/app/services/reminder_service.py` — fetch saved program from GuestProgram or BusinessProfile, return top-5 projects with rooms
- [x] T031 [US2] Implement `format_guest_day_before(user, program)` in `backend/app/services/reminder_service.py` — format message with top projects and rooms, or prompt for profiling if no program
- [x] T032 [US2] Implement `format_business_day_before(user, program)` in `backend/app/services/reminder_service.py` — format message with personalized project selection
- [x] T033 [US2] Implement `send_guest_reminders(session, batch_id, bot)` in `backend/app/services/reminder_service.py` — iterate guests, send with delay, create Notifications
- [x] T034 [US2] Update `execute_batch()` to include guest + business sending for day_before
- [x] T035 [US2] Handle guests without program — send "Пройдите профилирование" with button

**Checkpoint**: Day-before reminders work for all 4 roles (students, experts, guests, business).

---

## Phase 6: User Story 3 — Напоминание «за час» всем участникам (Priority: P2)

**Goal**: Краткие напоминания за час до начала DD для всех активных участников

**Independent Test**: Установить event start_date на сегодня, запустить "за час" — проверить короткие сообщения всем ролям

### Implementation for User Story 3

- [x] T036 [US3] Implement `format_student_hour_before(participation)` in `backend/app/services/reminder_service.py` — short message "Через час — твоё выступление! Зал X"
- [x] T037 [US3] Implement `format_expert_hour_before(assignment, first_project)` in `backend/app/services/reminder_service.py` — short message with room and first project
- [x] T038 [US3] Implement `format_guest_hour_before(user, program)` in `backend/app/services/reminder_service.py` — short message "DD начинается через час"
- [x] T039 [US3] Update `send_student_reminders()` to accept reminder_type parameter, format based on type
- [x] T040 [US3] Update `send_expert_reminders()` to accept reminder_type parameter
- [x] T041 [US3] Update `send_guest_reminders()` to accept reminder_type parameter
- [x] T042 [US3] Update `execute_batch()` to handle hour_before type

**Checkpoint**: Hour-before reminders work for all roles with shorter messages.

---

## Phase 7: REST API (Optional, for Admin UI)

**Purpose**: REST endpoints for viewing reminder batch history and details

- [x] T043 [P] Create `backend/app/api/reminders.py` with router
- [x] T044 [P] Implement `GET /api/v1/reminders/batches` — list batches for event, organizer-only
- [x] T045 [P] Implement `GET /api/v1/reminders/batches/{batch_id}` — batch details with notifications
- [x] T046 [P] Implement `POST /api/v1/reminders/preview` — get preview counts
- [x] T047 Register reminders router in `backend/app/main.py`

**Checkpoint**: REST API endpoints work per contracts/api.yaml.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, cleanup, validation

- [ ] T048 Verify Telegram message stays within 4096 char limit — truncate program list if needed
- [ ] T049 Handle interrupted batch — detect in_progress batch, offer resume
- [x] T050 Add logging for reminder operations — batch start/complete, send errors
- [x] T051 Add telegram_chat_id population in expert bot start flow (update `backend/app/services/invite_service.py` handle_expert_start)
- [ ] T052 Run quickstart.md scenarios 1-10 end-to-end validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — T001-T004 can run in parallel, T005-T007 sequential
- **Phase 2 (Foundational)**: Depends on T001 (models), T002 (schemas). T008-T014 mostly sequential (T014 keyboards can parallel)
- **Phase 3 (US4)**: Depends on Phase 2 complete. Entry point for all reminders.
- **Phase 4 (US1)**: Depends on Phase 3 (T018 execute_batch stub). Core sending logic.
- **Phase 5 (US2)**: Depends on Phase 4 (extends execute_batch). Adds guest/business.
- **Phase 6 (US3)**: Depends on Phase 4 (refactors format functions). Adds hour_before.
- **Phase 7 (REST)**: Can start after Phase 2. Independent of bot phases.
- **Phase 8 (Polish)**: Depends on all functional phases complete.

### User Story Dependencies

- **User Story 4 (P2)**: MUST be first — it's the entry point (`/remind` command)
- **User Story 1 (P1)**: Core sending logic, depends on US4 command flow
- **User Story 2 (P1)**: Extends US1 with guest/business recipients
- **User Story 3 (P2)**: Extends US1/US2 with hour_before message variants

### Within Each Phase

- Models before services (services import models)
- Schemas before API endpoints (endpoints use schemas)
- Service functions before bot handlers (handlers call services)
- Keyboards before handlers that use them

### Parallel Opportunities

- T001, T002, T003, T004 — all parallel (different files)
- T043, T044, T045, T046 — parallel within Phase 7 (independent endpoints)
- T048, T049, T050 — parallel (independent concerns)

---

## Parallel Example: Phase 1 Setup

```bash
# Launch all setup tasks in parallel:
Task: "Create reminder models in backend/app/models/reminder.py"
Task: "Create reminder schemas in backend/app/schemas/reminder.py"
Task: "Create empty reminder_service.py with stubs"
Task: "Create empty reminder handler with stubs"

# Then sequential:
Task: "Generate Alembic migration"
Task: "Run migration"
Task: "Register models"
```

---

## Implementation Strategy

### MVP First (Phase 1-4)

1. Complete Phase 1: Setup (models, schemas, stubs, migration)
2. Complete Phase 2: Foundational (service logic, keyboards)
3. Complete Phase 3: US4 — `/remind` command with preview/confirm flow
4. Complete Phase 4: US1 — Student + Expert day-before sending
5. **STOP and VALIDATE**: Test via quickstart.md Scenario 1
6. Demo: Organizer can send reminders to students + experts

### Full Delivery (Phase 5-8)

1. Add Phase 5: US2 — Guest + Business recipients
2. Add Phase 6: US3 — Hour-before message variants
3. Add Phase 7: REST API (if admin UI needed)
4. Add Phase 8: Polish, edge cases, logging
5. Final validation: All 10 quickstart scenarios pass

---

## Notes

- [P] tasks = different files, no dependencies
- [US*] label maps task to specific user story
- US4 implemented first despite P2 priority — it's the command entry point
- Rate limiting (0.04s delay) reuses pattern from participation_service.broadcast_slots
- telegram_chat_id on Expert needed for messaging — populate on bot_started
- Commit after each task or logical group
