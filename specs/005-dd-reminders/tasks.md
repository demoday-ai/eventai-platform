# Tasks: DD Reminders & Timing Shift Notifications

**Input**: Design documents from `/specs/005-dd-reminders/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app (backend-only)**: `backend/app/` for source, `backend/alembic/` for migrations
- Follows existing structure from EPIC-001 through EPIC-004

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration and shared models/schemas for schedule and notification system

- [x] T001 Create Alembic migration `004_dd_reminders.py` in `backend/alembic/versions/004_dd_reminders.py` — 3 new tables: `schedule_slots`, `notifications`, `schedule_change_logs` with all columns, indexes, and constraints per `data-model.md`
- [x] T002 [P] Create ScheduleSlot model in `backend/app/models/schedule_slot.py` — fields: event_id, room_id, project_id, clustering_run_id, start_time, end_time, display_order, status, status_changed_at, updated_at; relationships to Event, Room, Project, ClusteringRun; status values: scheduled/moved/cancelled
- [x] T003 [P] Create Notification model in `backend/app/models/notification.py` — fields: event_id, user_id, schedule_slot_id (nullable), type, content, status, scheduled_at, sent_at, retry_count, error_message, batch_key; relationships to User, Event, ScheduleSlot; type values: eve_of_dd/pre_slot/timing_shift/program_cancelled; status values: pending/sent/failed/cancelled/batched
- [x] T004 [P] Create ScheduleChangeLog model in `backend/app/models/schedule_change_log.py` — fields: schedule_slot_id, event_id, changed_by_user_id, change_type, old_start_time, old_end_time, old_room_id, new_start_time, new_end_time, new_room_id, notifications_sent; relationships to ScheduleSlot, User, Room (old/new); change_type values: time_changed/room_changed/time_and_room_changed/cancelled/restored
- [x] T005 Register new models in `backend/app/models/__init__.py` — add ScheduleSlot, Notification, ScheduleChangeLog to `__all__` and imports
- [x] T006 [P] Create Pydantic schemas in `backend/app/schemas/schedule.py` — ScheduleSlotResponse, ScheduleGenerateRequest, ScheduleGenerateResult, SlotUpdateRequest, SlotUpdateResult, ScheduleResponse (grouped by room/day), ReminderPreview, ReminderSendResult, NotificationDashboard, NotificationListResponse, ScheduleChangeListResponse per `contracts/api.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core services that MUST be complete before ANY user story — schedule generation and notification delivery engine

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Implement schedule generation logic in `backend/app/services/schedule_service.py` — function `generate_schedule(session, event_id, clustering_run_id, day1_start, day1_end, day2_start, day2_end, slot_duration_minutes=15)`: find approved clustering run, iterate room_projects, create 15-min ScheduleSlot records with sequential start_times per room; support multi-day via event start_date/end_date; Day 1 default 10:30-19:30, Day 2 default 14:00-19:30 MSK; validate no duplicate slots for same project+run; return ScheduleGenerateResult
- [x] T008 Implement schedule CRUD in `backend/app/services/schedule_service.py` — functions: `get_schedule(session, event_id, room_id=None, day=None, status=None)` returns slots grouped by day/room; `update_slot(session, slot_id, update_data, changed_by_user_id)` handles time/room/status changes, creates ScheduleChangeLog entry, returns old values for notification; `approve_schedule(session, event_id, clustering_run_id)` sets `clustering_runs.schedule_approved_at = now()` for the given run; `get_change_log(session, event_id, slot_id=None, limit=50)`
- [x] T009 Implement notification delivery engine in `backend/app/services/notification_service.py` — function `send_notification(session, notification_id, bot)`: load notification, send via `bot.send_message(chat_id=user.telegram_user_id, text=content)`, handle Telegram API errors, update status to sent/failed, increment retry_count; `send_bulk_notifications(session, notification_ids, bot)`: throttled send with asyncio.Semaphore(25) and asyncio.sleep(0.05) between sends; `retry_failed(session, event_id, bot)`: find notifications with status=failed and retry_count < 3, retry with exponential backoff
- [x] T010 Implement escalation integration in `backend/app/services/notification_service.py` — function `create_notification_escalation(session, notification, event_id)`: when notification status=failed after 3 retries or user has no telegram_user_id, create Escalation record with type `notification_undeliverable` or `reminder_send_failed`; reuse existing Escalation model from EPIC-004

**Checkpoint**: Foundation ready — schedule can be generated and notifications can be sent. User story implementation can begin.

---

## Phase 3: User Story 1 - Eve-of-DD Reminders for All Participants (Priority: P1) 🎯 MVP

**Goal**: Automatically send personalized reminder messages to all confirmed participants (students, experts, guests, business) the evening before Demo Day, with organizer preview and cancel capability.

**Independent Test**: Generate schedule from approved clustering, trigger eve-of-DD reminders manually via API or bot, verify each role receives correctly formatted message with their schedule details.

### Implementation for User Story 1

- [x] T011 [US1] Implement reminder message templates in `backend/app/services/notification_service.py` — function `build_eve_reminder(user, role, schedule_slots, event)` returns personalized text per role: student → room + time + "Удачи!"; expert → room + time + project list; guest/business → personal program list (or fallback "Используйте /program" if no profiling data); all times formatted in Moscow time (UTC+3); messages in Russian; respect 4096 char Telegram limit with truncation
- [x] T012 [US1] Implement eve-of-DD reminder job in `backend/app/services/notification_service.py` — function `send_eve_reminders(session, event_id, target_day, bot)`: query all users with roles for event, join with schedule data (students → their slot, experts → their room assignments + room's projects, guests/business → personal program or fallback), build personalized message per user, create Notification records with type=eve_of_dd and status=pending, call `send_bulk_notifications()`; filter only users with `telegram_user_id` set; create escalation for unreachable users; return ReminderSendResult (sent/failed/skipped counts)
- [x] T013 [US1] Implement organizer preview in `backend/app/services/notification_service.py` — function `preview_reminders(session, event_id, target_day)`: count recipients by role (students/experts/guests/business), generate sample message for each role, list unreachable participants (no telegram_user_id or never started bot), calculate `can_cancel` based on current time vs scheduled send time (18:00 MSK - 1h = 17:00 MSK); return ReminderPreview
- [x] T014 [US1] Implement cancel reminders in `backend/app/services/notification_service.py` — function `cancel_reminders(session, event_id, target_day)`: find all pending notifications with type=eve_of_dd for target_day; if current time >= 17:00 MSK on target_day, raise `CancellationWindowClosedError` with message "Отмена рассылки возможна до 17:00"; otherwise update status to cancelled and return cancelled count
- [x] T015 [US1] Implement schedule REST API router in `backend/app/api/schedule.py` — endpoints: `POST /schedule/generate` (calls schedule_service.generate_schedule), `GET /schedule` (calls schedule_service.get_schedule), `POST /schedule/approve` (calls schedule_service.approve_schedule); all organizer-only with auth check against `settings.organizer_telegram_ids`
- [x] T016 [US1] Implement reminders REST API in `backend/app/api/schedule.py` — endpoints: `GET /reminders/preview` (calls notification_service.preview_reminders), `POST /reminders/cancel` (calls notification_service.cancel_reminders), `POST /reminders/send` (calls notification_service.send_eve_reminders manually); all organizer-only
- [x] T017 [US1] Register API router in `backend/app/main.py` — import schedule router from `backend/app/api/schedule.py`, add `app.include_router(schedule_router, prefix="/api/v1")` alongside existing routers
- [x] T018 [US1] Implement APScheduler eve-of-DD jobs in `backend/app/main.py` — add two new scheduled jobs: (1) preview job at 17:00 MSK day before each event day: sends preview to all organizer_telegram_ids with inline buttons [✅ Подтвердить] [❌ Отменить]; (2) send job at 18:00 MSK day before each event day: checks if cancelled flag is set, if not → calls `send_eve_reminders()`; use CronTrigger with timezone='Europe/Moscow'; calculate dates from current event's start_date/end_date
- [x] T019 [US1] Implement bot handler for schedule management in `backend/app/bot/handlers/schedule.py` — ConversationHandler for `/schedule` command (organizer-only): states MENU → GENERATE → REVIEW_ROOM → ADJUST_SLOT → APPROVE; MENU shows buttons: "Сгенерировать расписание" / "Просмотреть расписание" / "Утвердить расписание" / "Превью напоминаний" / "Дашборд доставки"; GENERATE calls schedule_service.generate_schedule and shows summary; REVIEW_ROOM shows slots per room with inline buttons; APPROVE calls schedule_service.approve_schedule
- [x] T020 [US1] Implement bot callback for organizer preview/cancel in `backend/app/bot/handlers/schedule.py` — CallbackQueryHandler patterns: `sched_preview_confirm:{day}` → mark as confirmed (no-op, send will proceed); `sched_preview_cancel:{day}` → call notification_service.cancel_reminders, reply "Рассылка отменена"
- [x] T021 [US1] Register schedule bot handlers in `backend/app/bot/app.py` — import and add `get_schedule_handler()` ConversationHandler and `schedule_preview_callback` / `schedule_cancel_callback` CallbackQueryHandlers

**Checkpoint**: Eve-of-DD reminders fully functional — organizer can generate schedule, preview, cancel, and reminders auto-send at 18:00 MSK.

---

## Phase 4: User Story 2 - Pre-Slot Reminders (Priority: P2)

**Goal**: Send "1 hour before" reminders to participants on Demo Day itself, with deduplication and 30-minute cooldown.

**Independent Test**: Create a slot starting 1 hour from now, run the pre-slot checker, verify participant receives exactly one reminder; run checker again and verify no duplicate is sent.

### Implementation for User Story 2

- [x] T022 [US2] Implement pre-slot reminder message templates in `backend/app/services/notification_service.py` — function `build_pre_slot_reminder(user, role, schedule_slot)`: student → "Через час — твоё выступление в [Зал X]!"; expert → "Через час — начало оценки в [Зал X]!"; guest/business → "Через час — [top project title] в [Зал X]!" (single highest-relevance project from personal program)
- [x] T023 [US2] Implement pre-slot checker in `backend/app/services/notification_service.py` — function `check_and_send_pre_slot_reminders(session, event_id, bot)`: find all schedule_slots with status=scheduled where start_time is between now+55min and now+65min (MSK); for each slot, find affected participants (student for that project, experts assigned to that room, guests/business with project in program); check dedup: skip if notification exists for (user_id, slot_id, type=pre_slot) with status != failed; check 30-min cooldown: skip if any pre_slot notification sent to user in last 30 min; create Notification records, call send_bulk_notifications()
- [x] T024 [US2] Register APScheduler pre-slot job in `backend/app/main.py` — add IntervalTrigger(minutes=5) job that: checks if today is an event day (between event.start_date and event.end_date), if within event hours (start_time - 1h to end_time), calls `check_and_send_pre_slot_reminders()`; use timezone='Europe/Moscow' for all comparisons

**Checkpoint**: Pre-slot reminders fire automatically every 5 min on DD day with proper dedup.

---

## Phase 5: User Story 3 - Timing Shift Notifications (Priority: P2)

**Goal**: When organizer changes schedule, automatically notify affected participants with old/new time/room, with 5-minute batching for rapid changes.

**Independent Test**: Move a project's slot via bot or API, verify affected student/expert/guest receives notification with old and new time within 5 minutes. Make 3 rapid changes and verify participant gets one batched message.

### Implementation for User Story 3

- [x] T025 [US3] Implement slot update with change detection in `backend/app/services/schedule_service.py` — extend `update_slot()` to: detect what changed (time, room, both, cancelled, restored), create ScheduleChangeLog with old/new values, return change_log record; also handle slot cancellation (set status=cancelled) and restoration (set status=scheduled)
- [x] T026 [US3] Implement timing shift notification queueing in `backend/app/services/notification_service.py` — function `queue_timing_shift_notifications(session, change_log, event_id)`: find all affected participants (student of the project, experts in old/new room, guests/business with project in program); for each participant create Notification with type=timing_shift, status=pending, batch_key=f"{user_id}:{event_id}:timing_shift" and scheduled_at=now+5min; if a pending notification with same batch_key exists, mark it as batched and create a new combined notification
- [x] T027 [US3] Implement notification batch processor in `backend/app/services/notification_service.py` — function `process_pending_batches(session, bot)`: find all pending notifications with type=timing_shift where scheduled_at <= now; group by user_id; for each user, collect all pending timing_shift notifications, build single batch message ("📋 Изменения в расписании:\n• Проект X: время1 → время2\n• Проект Y: ..."), send as one message, mark all source notifications as batched, create one new sent notification
- [x] T028 [US3] Register APScheduler batch processor job in `backend/app/main.py` — add IntervalTrigger(seconds=60) job that calls `process_pending_batches()`; runs continuously (not just on DD day, since organizer may adjust schedule the day before)
- [x] T029 [US3] Implement bot handler for slot adjustment in `backend/app/bot/handlers/schedule.py` — extend REVIEW_ROOM state: when organizer taps a slot, show inline buttons "Перенести время" / "Перенести в другой зал" / "Отменить слот"; "Перенести время" → ask for new time (inline time picker with 15-min increments); "Перенести в другой зал" → show room list; "Отменить слот" → confirm and cancel; all changes call schedule_service.update_slot() which triggers queue_timing_shift_notifications()
- [x] T030 [US3] Implement PATCH /schedule/slots/{slot_id} endpoint in `backend/app/api/schedule.py` — parse SlotUpdateRequest, call schedule_service.update_slot(), then notification_service.queue_timing_shift_notifications() with the change_log, return SlotUpdateResult with notifications_queued count

**Checkpoint**: Schedule changes trigger automatic batched notifications to all affected participants.

---

## Phase 6: User Story 4 - Organizer Reminder Dashboard (Priority: P3)

**Goal**: Organizer sees delivery statistics, unreachable participants, and timing shift notification log.

**Independent Test**: Send some reminders (including a few that fail), then request dashboard and verify counts match.

### Implementation for User Story 4

- [x] T031 [US4] Implement dashboard queries in `backend/app/services/notification_service.py` — function `get_notification_dashboard(session, event_id, type_filter=None, day_filter=None)`: aggregate notifications by status (sent/failed/pending), by role (join users → user_roles → roles), by type; list unreachable participants (users with no telegram_user_id or notifications with status=failed after 3 retries); return NotificationDashboard
- [x] T032 [US4] Implement GET /notifications/dashboard endpoint in `backend/app/api/schedule.py` — organizer-only; parse query params (type, day), call get_notification_dashboard(), return NotificationDashboard response
- [x] T033 [US4] Implement GET /notifications endpoint in `backend/app/api/schedule.py` — list notifications with filters (user_id, type, status, limit, offset); return NotificationListResponse
- [x] T034 [US4] Implement GET /schedule/changes endpoint in `backend/app/api/schedule.py` — list schedule change logs with filters (slot_id, limit); return ScheduleChangeListResponse including `notifications_sent` count per change; for detailed notification recipients, use GET /notifications with type=timing_shift filter (T033)
- [x] T035 [US4] Implement bot dashboard command in `backend/app/bot/handlers/schedule.py` — extend MENU state: "Дашборд доставки" button → query notification_service.get_notification_dashboard(), format as Telegram message: "📊 Доставка напоминаний\n\n✅ Отправлено: N\n❌ Ошибка: N\n⏳ В очереди: N\n\nПо ролям:\n👨‍🎓 Студенты: N отпр. / N ошибка\n👨‍🏫 Эксперты: N отпр. / N ошибка\n👤 Гости: N отпр. / N ошибка\n💼 Бизнес: N отпр. / N ошибка"; if unreachable > 0, add "⚠️ Недоступны: N участников [Показать список]" button

**Checkpoint**: Organizer has full visibility into notification delivery via bot and API.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, multi-day support, graceful degradation, final integration

- [x] T036 [P] Handle multi-day event edge cases in `backend/app/services/notification_service.py` — ensure eve-of-DD job sends separate reminders per day; participant with items on both days gets two messages (one per day, listing only that day's items); pre-slot job only processes slots for the current day
- [x] T037 [P] Handle program cancellation notification in `backend/app/services/notification_service.py` — when all projects in a guest/business personal program are cancelled (all slots cancelled), send notification: "Все проекты из вашей программы были отменены. Обратитесь к организатору." with type=program_cancelled
- [x] T038 [P] Implement graceful degradation for guest/business without profiling in `backend/app/services/notification_service.py` — if personal program data doesn't exist (EPIC-005/006 not implemented), send fallback message: "Завтра Demo Day! Используйте /program чтобы получить персональную подборку."
- [ ] T039 Validate quickstart.md flow end-to-end — follow all steps in `specs/005-dd-reminders/quickstart.md` from schedule generation through reminder sending and dashboard; verify each step works as documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 — core MVP
- **User Story 2 (Phase 4)**: Depends on Phase 2 — can run in parallel with US1 (different service functions, same files but non-overlapping)
- **User Story 3 (Phase 5)**: Depends on Phase 2 + T008 (schedule CRUD with change detection) — can partially overlap with US1/US2
- **User Story 4 (Phase 6)**: Depends on Phase 2 — reads notification data, no writes; can run after US1 delivers some data
- **Polish (Phase 7)**: Depends on US1-US4 completion

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2. Core MVP — must complete first.
- **US2 (P2)**: Independent after Phase 2. Reuses notification_service from Phase 2. Can overlap with US1.
- **US3 (P2)**: Depends on schedule CRUD (T008). Extends update_slot() from Phase 2. Can overlap with US1/US2.
- **US4 (P3)**: Independent after Phase 2. Read-only queries on notification data. Can start after US1 creates some notifications.

### Within Each User Story

- Models → Services → API endpoints → Bot handlers
- Service functions can be developed independently when in different functions
- Bot handlers depend on service functions being complete

### Parallel Opportunities

- **Phase 1**: T002, T003, T004, T006 can all run in parallel (different files)
- **Phase 2**: T007 and T009 can start in parallel (schedule_service.py vs notification_service.py)
- **Phase 3**: T015/T016 (API) and T019/T020 (bot) can run in parallel after T011-T014 (service)
- **Across stories**: US1 and US2 use different service functions — their implementation tasks can overlap
- **Phase 6**: T031-T035 are mostly additive queries — low conflict risk with other phases

---

## Parallel Example: Phase 1 Setup

```bash
# Launch all model files together:
Task: "Create ScheduleSlot model in backend/app/models/schedule_slot.py"
Task: "Create Notification model in backend/app/models/notification.py"
Task: "Create ScheduleChangeLog model in backend/app/models/schedule_change_log.py"
Task: "Create Pydantic schemas in backend/app/schemas/schedule.py"
```

## Parallel Example: User Story 1 API + Bot

```bash
# After service functions (T011-T014) are complete, launch API and bot in parallel:
Task: "Implement schedule REST API router in backend/app/api/schedule.py"
Task: "Implement bot handler for schedule management in backend/app/bot/handlers/schedule.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (migration + models + schemas)
2. Complete Phase 2: Foundational (schedule generation + notification engine)
3. Complete Phase 3: User Story 1 (eve-of-DD reminders with preview/cancel)
4. **STOP and VALIDATE**: Generate schedule from seed data, trigger reminders manually, verify messages per role
5. Deploy/demo if ready — this alone covers the RICE-760 highest priority feature

### Incremental Delivery

1. Setup + Foundational → Schedule exists, notifications can be sent
2. Add US1 → Eve-of-DD reminders (MVP, highest value)
3. Add US2 → Pre-slot reminders on DD day (incremental value)
4. Add US3 → Timing shift notifications (addresses key interview pain point)
5. Add US4 → Organizer dashboard (operational visibility)
6. Polish → Edge cases, multi-day, graceful degradation

### Parallel Team Strategy

With 3 developers (Дима, Настя, Иван) + Claude:

1. **Together**: Phase 1 + Phase 2 (foundational infrastructure)
2. Once foundational is done:
   - **Настя**: User Story 1 (eve-of-DD reminders — MVP)
   - **Иван**: User Story 2 (pre-slot reminders) + User Story 3 (timing shifts)
   - **Claude**: User Story 4 (dashboard queries) + Phase 7 (polish)
3. Integration and demo validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All times in Moscow timezone (UTC+3) — use `Europe/Moscow` for APScheduler
- Telegram throttling: asyncio.Semaphore(25) + sleep(0.05) between sends
- No LLM dependency — all reminders are template-based, no AI calls
- Escalation reuse from EPIC-004 — new types `notification_undeliverable` and `reminder_send_failed`
- Total: 39 tasks (6 setup, 4 foundational, 11 US1, 3 US2, 6 US3, 5 US4, 4 polish)
