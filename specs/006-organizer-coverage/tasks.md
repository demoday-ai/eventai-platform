# Tasks: Дашборд покрытия тематик для организатора (EPIC-006)

**Input**: Design documents from `/specs/006-organizer-coverage/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api.yaml, quickstart.md

**Tests**: Not explicitly requested — manual validation via bot + API.

**Key Context**: REST API coverage endpoints already exist in EPIC-004 (`invite_service.get_coverage_dashboard`, `get_room_coverage_detail`). Bot coverage states exist in `expert_assignment.py` (COVERAGE_DASHBOARD, COVERAGE_ROOM_DETAIL). EPIC-006 extends with project counts, tag analysis, gap detection, bot `/coverage` command, and enriched schemas.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new files, Pydantic schemas for enriched coverage responses

- [ ] T001 [P] Create coverage response schemas in `backend/app/schemas/coverage.py` — RoomCoverage, CoverageSummary, RoomExpert, ExpertCandidate, CoverageGap, RoomCoverageDetail, CoverageGapsList per contracts/api.yaml
- [ ] T002 [P] Create empty `backend/app/services/coverage_service.py` with function stubs: `get_coverage_summary()`, `get_room_detail()`, `get_coverage_gaps()`, `find_expert_candidates()`
- [ ] T003 [P] Create empty `backend/app/bot/handlers/coverage.py` with stub for `/coverage` command handler

**Checkpoint**: New files exist with stubs. No functionality yet.

---

## Phase 2: Foundational (Core Service Logic)

**Purpose**: Implement `coverage_service.py` — the read-only aggregation layer that all user stories depend on

**⚠️ CRITICAL**: Bot handler and API enrichment depend on service being complete

- [ ] T004 [US1] Implement `get_coverage_summary(session, event_id)` in `backend/app/services/coverage_service.py` — returns per-room project_count, top_tags (top 5 by frequency), confirmed/pending/declined expert counts, coverage_level. Uses rooms, room_projects, project_tags, expert_room_assignments tables. Gets approved clustering via `matching_service.get_approved_clustering()`
- [ ] T005 [US2] Implement `get_room_detail(session, event_id, room_id)` in `backend/app/services/coverage_service.py` — returns expert list (id, name, status, match_score, tags, bot_started), all distinct project_tags in room, uncovered_tags (project tags minus confirmed expert tags), and candidate experts for gaps
- [ ] T006 [US3] Implement `find_expert_candidates(session, tag_name, exclude_room_id, clustering_run_id)` in `backend/app/services/coverage_service.py` — finds experts with matching tag not assigned to target room, returns expert_id, name, matching_tags, current_rooms
- [ ] T007 [US3] Implement `get_coverage_gaps(session, event_id)` in `backend/app/services/coverage_service.py` — iterates all rooms, collects uncovered tags per room with project count and candidate experts. Returns CoverageGapsList

**Checkpoint**: Service layer complete. All 4 functions return correct data from DB.

---

## Phase 3: User Story 1 — Сводка покрытия по залам (Priority: P1) 🎯 MVP

**Goal**: Организатор отправляет `/coverage` и видит все залы с подтверждёнными/приглашёнными экспертами, проектами, статусами

**Independent Test**: Отправить `/coverage` в боте — проверить что показаны все залы с корректными счётчиками

### Implementation for User Story 1

- [ ] T008 [US1] Add coverage keyboard functions in `backend/app/bot/keyboards.py` — `coverage_summary_keyboard(rooms_data)` with room buttons (🟢/🟡/🔴 indicators + project count), callback pattern `cov_room:<room_id[:8]>`, and 🔄 refresh button with callback `cov:refresh`
- [ ] T009 [US1] Implement `/coverage` command handler in `backend/app/bot/handlers/coverage.py` — check organizer access (organizer_ids from settings), call `coverage_service.get_coverage_summary()`, format Telegram message with emoji indicators (✅/⚠️/❌), project counts, expert counts, totals line. Use `coverage_summary_keyboard()`. Handle no-approved-clustering edge case
- [ ] T010 [US1] Register coverage handler in `backend/app/bot/app.py` — import and add CommandHandler for `/coverage` + CallbackQueryHandler for `cov:refresh` pattern. Keep separate from existing expert_assignment coverage flow

**Checkpoint**: `/coverage` command works for organizers. Shows all rooms with correct counts and status indicators.

---

## Phase 4: User Story 2 — Детализация по залу (Priority: P1)

**Goal**: Организатор нажимает на зал в сводке и видит экспертов с тегами, тематики проектов, непокрытые теги

**Independent Test**: Нажать кнопку зала из сводки — проверить что видны эксперты со статусами и тегами

### Implementation for User Story 2

- [ ] T011 [US2] Add room detail keyboard in `backend/app/bot/keyboards.py` — `coverage_room_detail_keyboard(room_id)` with ⬅️ back button (callback `cov:back`) and 🔄 refresh (callback `cov_room_refresh:<room_id[:8]>`)
- [ ] T012 [US2] Implement room drill-down callback in `backend/app/bot/handlers/coverage.py` — handle `cov_room:<room_id_prefix>` callback, resolve full room_id from DB, call `coverage_service.get_room_detail()`, format message: expert list (✅/⏳/❌ + name + tags), project tag summary, uncovered tags section. Handle room-not-found edge case
- [ ] T013 [US2] Wire drill-down callbacks in `backend/app/bot/app.py` — register CallbackQueryHandler for `cov_room:` pattern and `cov:back` pattern (returns to summary)

**Checkpoint**: Full flow works: `/coverage` → click room → see detail → back to summary.

---

## Phase 5: User Story 3 — Непокрытые тематики и рекомендации (Priority: P2)

**Goal**: Организатор видит все тематические пробелы + рекомендованных экспертов-кандидатов

**Independent Test**: Запросить `/gaps` или нажать кнопку пробелов — увидеть непокрытые теги с кандидатами

### Implementation for User Story 3

- [ ] T014 [US3] Add gaps button to coverage summary keyboard in `backend/app/bot/keyboards.py` — add ⚠️ "Непокрытые тематики" button with callback `cov:gaps` to `coverage_summary_keyboard()`
- [ ] T015 [US3] Implement gaps display in `backend/app/bot/handlers/coverage.py` — handle `cov:gaps` callback, call `coverage_service.get_coverage_gaps()`, format message: grouped by room, each gap shows tag + project count + candidate experts (name, current rooms). Handle "all covered" case. Add back button
- [ ] T016 [US3] Register gaps callback in `backend/app/bot/app.py` — add CallbackQueryHandler for `cov:gaps` pattern

**Checkpoint**: Gap analysis works: shows uncovered tags per room with expert recommendations.

---

## Phase 6: User Story 4 — REST API (Priority: P2)

**Goal**: Обогатить существующие REST API эндпоинты данными из coverage_service

**Independent Test**: `GET /api/v1/coverage` возвращает project_count, top_tags. `GET /api/v1/coverage/{room_id}` возвращает uncovered_tags, candidates. `GET /api/v1/coverage/gaps` возвращает все пробелы.

### Implementation for User Story 4

- [ ] T017 [US4] Update `GET /api/v1/coverage` endpoint in `backend/app/api/experts.py` — replace call to `invite_service.get_coverage_dashboard()` with `coverage_service.get_coverage_summary()`, use CoverageSummary schema for response. Add organizer-only check (403 for non-organizers)
- [ ] T018 [US4] Update `GET /api/v1/coverage/{room_id}` endpoint in `backend/app/api/experts.py` — replace call to `invite_service.get_room_coverage_detail()` with `coverage_service.get_room_detail()`, use RoomCoverageDetail schema for response. Add organizer-only check
- [ ] T019 [US4] Add new `GET /api/v1/coverage/gaps` endpoint in `backend/app/api/experts.py` — call `coverage_service.get_coverage_gaps()`, return CoverageGapsList schema. Organizer-only. Handle no-approved-clustering (404)

**Checkpoint**: All 3 REST endpoints return enriched coverage data per contracts/api.yaml.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, cleanup, validation

- [ ] T020 [P] Verify edge cases: no approved clustering returns graceful message (bot) / 404 (API), empty rooms shown with 0 projects, experts without tags shown without match info
- [ ] T021 [P] Verify Telegram message stays within 4096 char limit for 10+ rooms — truncate if needed
- [ ] T022 Run quickstart.md scenarios 1-6 end-to-end validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — all T001-T003 can run in parallel
- **Phase 2 (Foundational)**: Depends on T001 (schemas) and T002 (stubs). T004 first, then T005, T006, T007 (T006 is used by T005 and T007)
- **Phase 3 (US1)**: Depends on T004 (coverage summary service). T008 → T009 → T010
- **Phase 4 (US2)**: Depends on T005 (room detail service). T011 → T012 → T013. Can run parallel with Phase 3
- **Phase 5 (US3)**: Depends on T007 (gaps service). T014 → T015 → T016
- **Phase 6 (US4)**: Depends on Phase 2 complete. T017, T018, T019 can run [P] parallel
- **Phase 7 (Polish)**: Depends on all phases complete

### Within Each Phase

- Keyboards before handlers (handlers use keyboard functions)
- Handlers before registration (app.py imports handlers)
- Service functions before consumers (bot/API use service)

### Parallel Opportunities

- T001, T002, T003 — all parallel (different files)
- T017, T018, T019 — parallel within Phase 6 (same file but independent endpoints)
- T020, T021 — parallel (independent validation)
- Phase 3 and Phase 4 can overlap once their respective service functions are ready
