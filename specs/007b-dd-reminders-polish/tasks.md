# Tasks: DD Reminders Polish (EPIC-007b)

**Input**: Design documents from `/specs/007b-dd-reminders-polish/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, quickstart.md
**Parent**: EPIC-007 (DD Reminders) — must be complete

**Tests**: Manual validation via quickstart.md scenarios (10 scenarios).

**Key Context**: Polish epic extending EPIC-007. Modifies existing files, no new entities. Focus: message truncation (4096 limit), batch recovery, E2E validation.

## Phase 1: Setup

**Purpose**: Verify EPIC-007 is complete and working

- [x] T001 Verify EPIC-007 reminder_service.py exists and is functional
- [x] T002 Verify EPIC-007 reminder.py handler exists with /remind command
- [x] T003 Verify EPIC-007 keyboards have reminder keyboards

**Checkpoint**: EPIC-007 code is present and functional.

---

## Phase 2: User Story 1 — Безопасная отправка длинных сообщений (Priority: P1)

**Goal**: Защита от превышения лимита Telegram (4096 символов) через обрезку списка проектов

**Independent Test**: Создать гостя с программой из 20+ проектов, отправить напоминание — сообщение должно быть доставлено и читаемо.

### Implementation for User Story 1

- [ ] T004 [US1] Implement `truncate_message(text, max_len=4000)` helper in `backend/app/services/reminder_service.py` — return text as-is if under limit
- [ ] T005 [US1] Implement truncation logic in `truncate_message()` — find last complete project entry before limit, add "...и ещё N проектов" suffix
- [ ] T006 [US1] Update `format_guest_day_before()` in `backend/app/services/reminder_service.py` — pass project list through truncation before formatting
- [ ] T007 [US1] Update `format_business_day_before()` in `backend/app/services/reminder_service.py` — pass project list through truncation
- [ ] T008 [US1] Add logging for truncation events in `backend/app/services/reminder_service.py` — log original vs truncated length

**Checkpoint**: Messages with long project lists are truncated correctly, no Telegram API errors.

---

## Phase 3: User Story 2 — Восстановление прерванной рассылки (Priority: P2)

**Goal**: При запуске `/remind` обнаруживать прерванные рассылки и предлагать возобновление

**Independent Test**: Прервать рассылку на середине, перезапустить бот, выполнить `/remind` — получить предложение возобновить.

### Implementation for User Story 2

- [ ] T009 [US2] Implement `get_interrupted_batch(session, event_id)` in `backend/app/services/reminder_service.py` — query newest in_progress batch
- [ ] T010 [US2] Add `reminder_recovery_keyboard(batch_id)` in `backend/app/bot/keyboards.py` — buttons: "Возобновить" / "Начать заново" / "Отмена"
- [ ] T011 [US2] Update `remind_command()` in `backend/app/bot/handlers/reminder.py` — check for interrupted batch before showing type selection
- [ ] T012 [US2] Format interrupted batch message in `remind_command()` — show: started_at, sent/total progress
- [ ] T013 [US2] Add callback handler `recovery_choice_callback()` in `backend/app/bot/handlers/reminder.py` — pattern `rem:recover:`
- [ ] T014 [US2] Implement resume logic in `recovery_choice_callback()` — call `resume_batch()` if "Возобновить"
- [ ] T015 [US2] Implement `resume_batch(session, batch, bot)` in `backend/app/services/reminder_service.py` — query pending notifications, continue sending
- [ ] T016 [US2] Implement fresh start logic in `recovery_choice_callback()` — set old batch to `cancelled`, show type selection
- [ ] T017 [US2] Register `recovery_choice_callback` handler in `get_reminder_handlers()` in `backend/app/bot/handlers/reminder.py`

**Checkpoint**: Interrupted batches are detected and can be resumed or cancelled.

---

## Phase 4: User Story 3 — E2E валидация сценариев (Priority: P3)

**Goal**: Проверка всех 10 сценариев из quickstart.md

**Independent Test**: Последовательное выполнение сценариев 1-10 с проверкой ожидаемых результатов.

### Validation Tasks

- [ ] T018 [US3] Validate Scenario 1: Short program — no truncation
- [ ] T019 [US3] Validate Scenario 2: Long program — correct truncation with suffix
- [ ] T020 [US3] Validate Scenario 3: Interrupted batch — detection works
- [ ] T021 [US3] Validate Scenario 4: Resume — sends only pending recipients
- [ ] T022 [US3] Validate Scenario 5: Fresh start — cancels old batch
- [ ] T023 [US3] Validate Scenario 6: Multiple interrupted — only newest shown
- [ ] T024 [US3] Validate Scenario 7: Completed batch — no recovery prompt
- [ ] T025 [US3] Validate Scenario 8: Blocked user — handled gracefully
- [ ] T026 [US3] Validate Scenario 9: UTF-8 truncation — safe character boundaries
- [ ] T027 [US3] Validate Scenario 10: Full E2E — all roles receive correct messages

**Checkpoint**: All 10 quickstart.md scenarios pass.

---

## Phase 5: Polish & Edge Cases

**Purpose**: Edge cases, logging, cleanup

- [ ] T028 Handle empty message edge case in send functions — skip with status `skipped`
- [ ] T029 Ensure UTF-8 safe truncation — don't break multi-byte characters
- [ ] T030 Add comprehensive logging for recovery operations
- [ ] T031 Update tasks.md marking all completed tasks

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Already complete (EPIC-007 merged)
- **Phase 2 (US1)**: Independent — can start immediately
- **Phase 3 (US2)**: Independent of US1 — can run in parallel
- **Phase 4 (US3)**: Depends on US1 + US2 complete
- **Phase 5 (Polish)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies, start immediately
- **User Story 2 (P2)**: No dependencies, can parallel with US1
- **User Story 3 (P3)**: Depends on US1 + US2 (validation requires features)

### Parallel Opportunities

- T004-T008 (US1) and T009-T017 (US2) can run in parallel
- T018-T027 (US3) must be sequential after US1+US2

---

## Implementation Strategy

### MVP First (Phase 1-2)

1. Complete Phase 2: US1 — Message truncation
2. **STOP and VALIDATE**: Test via quickstart.md Scenarios 1-2
3. Demo: Long messages are safely truncated

### Full Delivery (Phase 3-5)

1. Complete Phase 3: US2 — Batch recovery
2. Validate via quickstart.md Scenarios 3-6
3. Complete Phase 4: US3 — Full E2E validation
4. Complete Phase 5: Polish and edge cases
5. Final validation: All 10 scenarios pass

---

## Notes

- No new files — all modifications to existing EPIC-007 code
- [US*] label maps task to specific user story
- US1 and US2 are independent — can be implemented in parallel
- US3 is pure validation — requires US1+US2 complete
- Commit after each user story completion
