# Tasks: Dashboard и прогресс

**Input**: Design documents from `/specs/019-admin-dashboard/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included (TDD required by Constitution Principle III)

**Organization**: Tasks grouped by user story. 7 user stories (3×P1, 3×P2, 1×P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/app/`, `backend/tests/`
- **Frontend**: `frontend/src/`

---

## Phase 1: Setup

**Purpose**: Branch, migration, base schemas — prerequisites for all backend work

- [ ] T001 Create and checkout branch `019-admin-dashboard` from `main`
- [ ] T002 Add `source` field to User model in `backend/app/models/user.py` (nullable str, default "bot")
- [ ] T003 Create Alembic migration for User.source field: `ALTER TABLE users ADD COLUMN source VARCHAR(10) DEFAULT 'bot'`
- [ ] T004 Run migration and verify with `alembic upgrade head`

---

## Phase 2: Foundational (Backend API — blocks all frontend stories)

**Purpose**: Extend backend schemas, services, and routes. All frontend user stories depend on these endpoints.

**⚠️ CRITICAL**: No frontend user story work can begin until this phase is complete.

### Backend Schemas

- [ ] T005 [P] Add `ProjectStats`, `PartnerStats`, `EventSummary` schemas in `backend/app/schemas/admin.py`
- [ ] T006 [P] Add `PipelineStatusResponse`, `Phase`, `Step`, `NextAction` schemas in `backend/app/schemas/admin.py`
- [ ] T007 Extend `DashboardResponse` with `event`, `projects`, `partners` fields in `backend/app/schemas/admin.py`
- [ ] T008 Update `RoomCoverage.coverage_status` enum to 5-level (gap/partial/covered/excellent/excess) in `backend/app/schemas/admin.py`

### Backend Service: Pipeline Status

- [ ] T009 Write tests for `get_pipeline_status()` in `backend/tests/test_admin_dashboard.py` — test all 9 step statuses, phase status derivation, next_action logic, empty state (no event)
- [ ] T010 Implement `get_pipeline_status()` in `backend/app/services/admin/dashboard_service.py` — query Event, Project, ParticipationRequest, User (expert), ClusteringRun, ExpertRoomAssignment, Notification to derive 9 step statuses; compute phase statuses and next_action

### Backend Service: Dashboard Extension

- [ ] T011 Write tests for extended `get_dashboard_stats()` in `backend/tests/test_admin_dashboard.py` — test projects count, partners count (by source), event summary with days_until, null event case
- [ ] T012 Extend `get_dashboard_stats()` in `backend/app/services/admin/dashboard_service.py` — add projects count query, partners count query (with source breakdown), event summary with days_until computation

### Backend Service: Coverage 5-level

- [ ] T013 Write tests for updated `get_coverage()` in `backend/tests/test_admin_dashboard.py` — test all 5 coverage levels (0→gap, 1→partial, 2→covered, 3→excellent, >3→excess)
- [ ] T014 Update `get_coverage_status()` logic in `backend/app/services/admin/dashboard_service.py` to return 5-level enum

### Backend Routes

- [ ] T015 Add `GET /api/v1/admin/pipeline-status` route in `backend/app/api/admin/dashboard.py` — calls `get_pipeline_status()`, returns PipelineStatusResponse
- [ ] T016 Write route-level test for pipeline-status endpoint in `backend/tests/test_admin_dashboard.py` — test 200 response shape, 401 unauthorized
- [ ] T017 Run all backend tests: `pytest backend/tests/test_admin_dashboard.py -v`

### Frontend API Client

- [ ] T018 [P] Add `PipelineStatusResponse`, `Phase`, `Step`, `NextAction` types in `frontend/src/lib/api-client.ts`
- [ ] T019 [P] Extend `DashboardData` type with `event`, `projects`, `partners` fields in `frontend/src/lib/api-client.ts`
- [ ] T020 Add `getPipelineStatus()` function in `frontend/src/lib/api-client.ts`
- [ ] T021 Create `usePipelineStatus()` hook in `frontend/src/hooks/usePipelineStatus.ts` — TanStack Query with refetchInterval: 30_000, placeholderData: keepPreviousData

**Checkpoint**: All backend endpoints ready, frontend types and hooks ready. Frontend story implementation can begin.

---

## Phase 3: User Story 1 — Пустой Dashboard: первый вход (Priority: P1) 🎯 MVP

**Goal**: Организатор без созданного события видит empty state с кнопкой перехода на Импорт. Global Stepper — все фазы серые.

**Independent Test**: Открыть Dashboard без активного события → карточка «Нет активного мероприятия» + кнопка «Перейти к импорту» + Stepper с 3 серыми фазами.

### Tests

- [ ] T022 [US1] Write test for EmptyState component in `frontend/src/components/dashboard/EmptyState.test.tsx` — renders message, renders button, button navigates to /import

### Implementation

- [ ] T023 [US1] Create `EmptyState` component in `frontend/src/components/dashboard/EmptyState.tsx` — card with «Нет активного мероприятия» text and «Перейти к импорту» button linking to /import
- [ ] T024 [US1] Rewrite `Dashboard` page in `frontend/src/pages/Dashboard.tsx` — conditional: if no event → EmptyState; else → full dashboard (placeholder for now). Use useQuery with refetchInterval: 30_000, placeholderData: keepPreviousData
- [ ] T025 [US1] Write test for Dashboard empty state rendering in `frontend/src/pages/Dashboard.test.tsx` — mock API returning null event → EmptyState shown

**Checkpoint**: Dashboard shows empty state when no event exists. MVP deliverable.

---

## Phase 4: User Story 2 — Global Stepper (Priority: P1)

**Goal**: Горизонтальная полоса прогресса с 3 фазами на каждой странице. Клик → навигация. Hover → подшаги.

**Independent Test**: Загрузить данные частично → Stepper показывает корректные статусы фаз; клик на фазу → переход; hover → подшаги.

**Dependencies**: Requires T021 (usePipelineStatus hook)

### Tests

- [ ] T026 [US2] Write tests for GlobalStepper in `frontend/src/components/dashboard/GlobalStepper.test.tsx` — renders 3 phases, correct status colors (completed/in_progress/not_started), click navigates to phase page, hover shows sub-steps

### Implementation

- [ ] T027 [US2] Create `GlobalStepper` component in `frontend/src/components/dashboard/GlobalStepper.tsx` — 3 phases with status indicators, click → navigate to first incomplete page of phase, hover/click → show sub-steps with statuses. Use usePipelineStatus() hook
- [ ] T028 [US2] Add GlobalStepper to `frontend/src/components/layout/AppLayout.tsx` — render between header and content area, conditionally show only for authenticated users

**Checkpoint**: Global Stepper visible on every page, reflects pipeline status, enables navigation.

---

## Phase 5: User Story 3 — Quick Action (Priority: P1)

**Goal**: Подсказка следующего незавершённого шага с кнопкой перехода. Скрывается когда всё готово.

**Independent Test**: Загрузить часть данных → Quick Action показывает конкретный следующий шаг + кнопка.

**Dependencies**: Requires T021 (usePipelineStatus hook — next_action field)

### Tests

- [ ] T029 [US3] Write tests for QuickAction in `frontend/src/components/dashboard/QuickAction.test.tsx` — renders label and link from next_action, navigates on button click, hidden when next_action is null

### Implementation

- [ ] T030 [US3] Create `QuickAction` component in `frontend/src/components/dashboard/QuickAction.tsx` — displays next_action.label + button linking to next_action.link; hidden when next_action is null
- [ ] T031 [US3] Integrate QuickAction into Dashboard page in `frontend/src/pages/Dashboard.tsx` — render below GlobalStepper area, above metrics

**Checkpoint**: Quick Action guides user to next step. Hidden when all complete.

---

## Phase 6: User Story 4 — Метрики мероприятия (Priority: P2)

**Goal**: 5 карточек метрик: проекты, студенты, эксперты, партнёры, залы.

**Independent Test**: Загрузить данные → 5 карточек с корректными числами; 0 если нет данных.

**Dependencies**: Requires T019 (extended DashboardData type)

### Tests

- [ ] T032 [US4] Write tests for MetricCards in `frontend/src/components/dashboard/MetricCards.test.tsx` — renders 5 cards with correct values, renders 0 for empty data

### Implementation

- [ ] T033 [US4] Create `MetricCards` component in `frontend/src/components/dashboard/MetricCards.tsx` — 5 cards (проекты, студенты, эксперты, партнёры, залы) with Lucide icons, responsive grid layout
- [ ] T034 [US4] Integrate MetricCards into Dashboard page in `frontend/src/pages/Dashboard.tsx`

**Checkpoint**: 5 metric cards visible with correct numbers.

---

## Phase 7: User Story 5 — Дата и обратный отсчёт (Priority: P2)

**Goal**: Дата мероприятия, обратный отсчёт в днях, ссылка для редактирования.

**Independent Test**: Создать событие с датой → дата и обратный отсчёт корректны; «сегодня» для текущего дня.

**Dependencies**: Requires T019 (event field in DashboardData)

### Tests

- [ ] T035 [US5] Write tests for EventCountdown in `frontend/src/components/dashboard/EventCountdown.test.tsx` — shows date and "через N дней", shows "сегодня" for today, shows "завершено" for past events, edit link navigates to /import

### Implementation

- [ ] T036 [US5] Create `EventCountdown` component in `frontend/src/components/dashboard/EventCountdown.tsx` — event name, date, days_until display (future → «через N дней», 0 → «сегодня», negative → «N дней назад»), edit link → /import
- [ ] T037 [US5] Integrate EventCountdown into Dashboard page in `frontend/src/pages/Dashboard.tsx` — render at top of dashboard content area

**Checkpoint**: Event date and countdown displayed correctly.

---

## Phase 8: User Story 6 — Покрытие залов экспертами (Priority: P2)

**Goal**: Таблица покрытия с 5-уровневой шкалой. Кнопка «Детали» для каждого зала.

**Independent Test**: Кластеризация одобрена, эксперты назначены → таблица с корректными статусами по 5 уровням; кнопка «Детали» → навигация.

**Dependencies**: Requires T008 + T014 (5-level coverage backend)

### Tests

- [ ] T038 [US6] Write tests for CoverageTable in `frontend/src/components/dashboard/CoverageTable.test.tsx` — renders room rows, correct coverage status labels/colors (gap/partial/covered/excellent/excess), "Детали" button navigates, hidden when no rooms

### Implementation

- [ ] T039 [US6] Create `CoverageTable` component in `frontend/src/components/dashboard/CoverageTable.tsx` — table with columns: зал, проекты, эксперты, статус (5-level with color indicators: gap→red, partial→yellow, covered→green, excellent→green, excess→blue); «Детали» button per row → /experts?room={id}
- [ ] T040 [US6] Integrate CoverageTable into Dashboard page in `frontend/src/pages/Dashboard.tsx` — render below metrics, hidden if coverage data is empty (no clustering)

**Checkpoint**: Coverage table with 5-level scale visible, navigation to room details works.

---

## Phase 9: User Story 7 — Auto-refresh (Priority: P3)

**Goal**: Данные обновляются каждые 30-60 секунд без мерцания и сброса скролла.

**Independent Test**: Открыть Dashboard в 2 вкладках, изменить данные — вторая обновится автоматически через 30-60 сек.

**Dependencies**: Cross-cutting — affects Dashboard and GlobalStepper (T024, T021)

### Tests

- [ ] T041 [US7] Write test for auto-refresh in `frontend/src/pages/Dashboard.test.tsx` — verify useQuery calls with refetchInterval: 30_000 and placeholderData: keepPreviousData for both dashboard and pipeline-status queries

### Implementation

- [ ] T042 [US7] Verify and finalize auto-refresh configuration in `frontend/src/pages/Dashboard.tsx` — ensure both dashboard and coverage queries use refetchInterval: 30_000, placeholderData: keepPreviousData. Verify no full-page re-render on refetch (skeleton only on initial load, not on refetch)

**Checkpoint**: Auto-refresh works without flicker or scroll reset.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, cleanup, full test run

- [ ] T043 [P] Full Dashboard integration test in `frontend/src/pages/Dashboard.test.tsx` — test complete happy path: event exists → Stepper + QuickAction + Metrics + Countdown + Coverage all render together
- [ ] T044 [P] Full backend test run: `pytest backend/tests/test_admin_dashboard.py -v --cov`
- [ ] T045 [P] Full frontend test run: `cd frontend && npm test -- --coverage`
- [ ] T046 Validate against quickstart.md scenarios — manually walk through all 5 demo scenarios
- [ ] T047 Verify coverage ≥80% for new code (backend + frontend)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (migration) — BLOCKS all frontend stories
- **US1 (Phase 3)**: Depends on Phase 2 (API + types ready)
- **US2 (Phase 4)**: Depends on Phase 2 (usePipelineStatus hook)
- **US3 (Phase 5)**: Depends on Phase 2 (next_action from pipeline-status)
- **US4 (Phase 6)**: Depends on Phase 2 (extended DashboardData)
- **US5 (Phase 7)**: Depends on Phase 2 (event field)
- **US6 (Phase 8)**: Depends on Phase 2 (5-level coverage)
- **US7 (Phase 9)**: Depends on US1 (Dashboard base is in place)
- **Polish (Phase 10)**: Depends on all stories complete

### User Story Dependencies

```
Phase 1 (Setup)
  └→ Phase 2 (Foundational)
       ├→ US1 (Phase 3) — Empty State 🎯 MVP
       ├→ US2 (Phase 4) — Global Stepper ──┐
       ├→ US3 (Phase 5) — Quick Action     │ can run in parallel
       ├→ US4 (Phase 6) — Метрики          │ after Phase 2
       ├→ US5 (Phase 7) — Дата/обратный    │
       ├→ US6 (Phase 8) — Покрытие залов ──┘
       └→ US7 (Phase 9) — Auto-refresh (after US1)
            └→ Phase 10 (Polish)
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Component before integration into Dashboard
- Story complete before moving to next priority (for single-developer flow)

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T005 + T006 (schemas — different schema groups, same file but independent sections)
- T009 + T011 + T013 (tests — independent test functions)
- T018 + T019 (frontend types — different type groups)

**After Phase 2 completes**:
- US1, US2, US3 (all P1) can start in parallel
- US4, US5, US6 (all P2) can start in parallel
- Within each story: test + component are sequential, but stories are independent

---

## Parallel Example: After Phase 2

```
# Developer A (P1 stories):
US1: T022 → T023 → T024 → T025    (Empty State)
US2: T026 → T027 → T028            (Global Stepper)
US3: T029 → T030 → T031            (Quick Action)

# Developer B (P2 stories):
US4: T032 → T033 → T034            (Метрики)
US5: T035 → T036 → T037            (Дата/обратный отсчёт)
US6: T038 → T039 → T040            (Покрытие залов)
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T021)
3. Complete Phase 3: US1 — Empty State (T022–T025)
4. **STOP and VALIDATE**: Dashboard shows empty state correctly
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Backend ready, types ready
2. US1 → Empty State → Deploy (MVP!)
3. US2 + US3 → Stepper + Quick Action → Deploy (wizard UX!)
4. US4 + US5 → Metrics + Countdown → Deploy (full dashboard!)
5. US6 → Coverage table → Deploy (monitoring!)
6. US7 → Auto-refresh → Deploy (polished!)
7. Polish → Tests, validation → Final release

### Single Developer Strategy (Recommended)

1. Phase 1 + Phase 2: Backend + frontend foundation (T001–T021)
2. Phase 3: US1 Empty State (T022–T025)
3. Phase 4: US2 Global Stepper (T026–T028)
4. Phase 5: US3 Quick Action (T029–T031)
5. Phase 6: US4 Metrics (T032–T034)
6. Phase 7: US5 Countdown (T035–T037)
7. Phase 8: US6 Coverage (T038–T040)
8. Phase 9: US7 Auto-refresh (T041–T042)
9. Phase 10: Polish (T043–T047)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD: Write tests first, verify they fail, then implement
- Commit after each phase completion
- Stop at any checkpoint to validate story independently
