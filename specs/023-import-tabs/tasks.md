# Tasks: Import Data Tabs

**Input**: Design documents from `/specs/023-import-tabs/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api.md ✅, quickstart.md ✅

**Tests**: TDD approach per project constitution. Tests included.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Add shadcn/ui Tabs component and backend schema

- [ ] T001 [P] Add shadcn/ui Tabs component in `frontend/src/components/ui/tabs.tsx`
- [ ] T002 [P] Add EventCreateRequest schema in `backend/app/schemas/admin.py`

---

## Phase 2: Foundational (Backend Endpoint)

**Purpose**: POST /admin/events endpoint — blocks US2 (event creation form)

- [ ] T003 Add POST `/api/v1/admin/events` endpoint in `backend/app/api/admin/events.py`
- [ ] T004 Add createEvent function in `frontend/src/lib/api-client.ts`
- [ ] T005 Write backend test for POST /admin/events in `backend/tests/test_admin_events.py`

**Checkpoint**: Backend event creation ready, frontend API client updated

---

## Phase 3: User Story 1 — Табы на странице импорта (Priority: P1) 🎯 MVP

**Goal**: Refactor DataImport page into 4 numbered tabs (Событие/Проекты/Эксперты/Гости)

**Independent Test**: Open /import → see 4 numbered tabs, switching preserves state, existing upload functionality works

### Implementation for User Story 1

- [ ] T006 [US1] Refactor `frontend/src/pages/DataImport.tsx` — wrap existing sections in Tabs layout with 4 tabs: «1. Событие», «2. Проекты», «3. Эксперты», «4. Гости». Tab «Событие» shows placeholder. Tabs «Проекты/Эксперты/Гости» contain existing upload sections unchanged.
- [ ] T007 [US1] Update `frontend/src/pages/DataImport.test.tsx` — add tests for tab rendering, tab switching, state preservation across tabs

**Checkpoint**: 4 tabs visible, switching works, existing uploads preserved, tab 1 has placeholder

---

## Phase 4: User Story 2 — Создание и редактирование мероприятия (Priority: P1)

**Goal**: Event creation/editing form on tab «Событие»

**Independent Test**: No event → form shows «Создать» button → fill and submit → event created. Event exists → form pre-filled → edit and save.

### Implementation for User Story 2

- [ ] T008 [US2] Implement event form in tab «Событие» inside `frontend/src/pages/DataImport.tsx` — creation mode (no event: name, start_date, end_date, description fields + «Создать» button) and edit mode (event exists: pre-filled form + «Сохранить» button). Use TanStack Query for GET /events/current, POST /admin/events, PATCH /admin/events/current. Validate end_date >= start_date.
- [ ] T009 [US2] Add tests for event form in `frontend/src/pages/DataImport.test.tsx` — test creation form, edit form, validation error, successful submit

**Checkpoint**: Event can be created and edited from Import page tab 1

---

## Phase 5: User Story 3 — Подсказки о порядке загрузки (Priority: P2)

**Goal**: Show hints on tabs 2-4 when event not created

**Independent Test**: Delete event → tabs 2-4 show hint «Сначала создайте мероприятие» with link to tab 1. Create event → hints disappear.

### Implementation for User Story 3

- [ ] T010 [US3] Add dependency hints in `frontend/src/pages/DataImport.tsx` — when no event exists, tabs «Проекты», «Эксперты», «Гости» show Alert with message «Сначала создайте мероприятие на вкладке "Событие"» and a button/link to switch to tab 1. When event exists, show normal upload UI.
- [ ] T011 [US3] Add tests for hints in `frontend/src/pages/DataImport.test.tsx` — test hint shown when no event, hint hidden when event exists, link navigates to tab 1

**Checkpoint**: Hints guide user through correct data loading order

---

## Phase 6: Polish & Cross-Cutting

- [ ] T012 Run quickstart.md verification checklist (10 scenarios)
- [ ] T013 Run full CI: backend tests + ruff, frontend tests + eslint + tsc --noEmit

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — T001, T002 in parallel
- **Phase 2 (Backend)**: T003 depends on T002. T004 depends on T003. T005 depends on T003.
- **Phase 3 (US1)**: T006 depends on T001. T007 depends on T006.
- **Phase 4 (US2)**: T008 depends on T004, T006. T009 depends on T008.
- **Phase 5 (US3)**: T010 depends on T008. T011 depends on T010.
- **Phase 6 (Polish)**: Depends on all phases complete

### User Story Dependencies

- **US1 (Tabs)**: Needs T001 (Tabs component). Independent of backend.
- **US2 (Event form)**: Needs US1 (tabs layout) + T003/T004 (backend endpoint + API client)
- **US3 (Hints)**: Needs US2 (event query logic to detect event presence)

### Implementation Strategy

Sequential: Setup → Backend → US1 → US2 → US3 → Polish

Total: 13 tasks, 3 user stories
