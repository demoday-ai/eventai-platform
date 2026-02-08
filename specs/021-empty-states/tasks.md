# Tasks: Empty States и подсказки

**Input**: Design documents from `/specs/021-empty-states/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Tests**: Included — TDD per Constitution Principle III (min 80% coverage).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create reusable PageEmptyState component + tests

- [ ] T001 [P] Create reusable PageEmptyState component in `frontend/src/components/ui/PageEmptyState.tsx` with props: icon (LucideIcon), title (string), description (string), actionLabel? (string), actionLink? (string). Dashed border card, centered layout, Lucide icon, shadcn Button as Link.
- [ ] T002 [P] Create PageEmptyState tests in `frontend/src/components/ui/PageEmptyState.test.tsx`: renders icon/title/description, renders action button when actionLabel+actionLink provided, no button when no actionLabel, button links to actionLink via react-router Link.

**Checkpoint**: Reusable component ready — user story implementation can begin.

---

## Phase 2: User Story 1 - Pipeline-dependent Empty States (Priority: P1) 🎯 MVP

**Goal**: Show empty states on ProjectsList, Clustering, ExpertMatching, Schedule when prerequisites are missing.

**Independent Test**: Open Clustering page with empty DB (no projects) — should show empty state with text and link to /import.

### Tests for User Story 1

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [ ] T003 [P] [US1] Test for ProjectsList empty state in `frontend/src/pages/ProjectsList.test.tsx`: when projects query returns empty array and no search/filter active, show PageEmptyState with "Проекты ещё не загружены" text and link to /import.
- [ ] T004 [P] [US1] Test for Clustering empty state in `frontend/src/pages/Clustering.test.tsx`: when projects count is 0, show PageEmptyState with "Для кластеризации необходимы проекты" text and link to /import.
- [ ] T005 [P] [US1] Test for ExpertMatching empty state in `frontend/src/pages/ExpertMatching.test.tsx`: when no approved clustering exists, show PageEmptyState with "Для матчинга экспертов необходима одобренная кластеризация" and link to /clustering.
- [ ] T006 [P] [US1] Test for Schedule empty state in `frontend/src/pages/Schedule.test.tsx`: when no approved clustering exists, show PageEmptyState with "Для генерации расписания необходима одобренная кластеризация" and link to /clustering.

### Implementation for User Story 1

- [ ] T007 [P] [US1] Add empty state to ProjectsList in `frontend/src/pages/ProjectsList.tsx`: check if projects array is empty AND no search/filter active → show PageEmptyState (FolderOpen icon, title "Проекты ещё не загружены", description "Загрузите проекты на странице Импорта", action "Перейти к импорту" → /import).
- [ ] T008 [P] [US1] Add empty state to Clustering in `frontend/src/pages/Clustering.tsx`: check if projects count is 0 (use existing query or add projects count check) → show PageEmptyState (Layers icon, title "Для кластеризации необходимы проекты", description "Загрузите проекты на странице Импорта", action "Перейти к импорту" → /import).
- [ ] T009 [P] [US1] Add empty state to ExpertMatching in `frontend/src/pages/ExpertMatching.tsx`: check if clustering is null/not approved → show PageEmptyState (Users icon, title "Для матчинга экспертов необходима одобренная кластеризация", description "Одобрите кластеризацию, чтобы начать матчинг", action "Перейти к кластеризации" → /clustering).
- [ ] T010 [P] [US1] Add empty state to Schedule in `frontend/src/pages/Schedule.tsx`: check if clustering is null/not approved → show PageEmptyState (Calendar icon, title "Для генерации расписания необходима одобренная кластеризация", description "Одобрите кластеризацию, чтобы генерировать расписание", action "Перейти к кластеризации" → /clustering).

**Checkpoint**: All 4 pipeline-dependent pages show empty states. Tests pass.

---

## Phase 3: User Story 2 - Messaging Empty States (Priority: P2)

**Goal**: Show tiered empty states on Messaging page: no event → no participants → normal UI.

**Independent Test**: Open Messaging page with empty DB — should show "Создайте мероприятие" empty state.

### Tests for User Story 2

- [ ] T011 [P] [US2] Test for Messaging empty states in `frontend/src/pages/Messaging.test.tsx`: (1) when isNoEventError → show "Создайте мероприятие" + link to /import; (2) when event exists but 0 participants → show "Загрузите участников" + link to /import; (3) when participants exist → show normal UI.

### Implementation for User Story 2

- [ ] T012 [US2] Add tiered empty states to Messaging in `frontend/src/pages/Messaging.tsx`: before rendering tabs, check (1) isNoEventError → PageEmptyState (MessageSquare icon, "Создайте мероприятие на странице Импорта", action → /import); (2) total participants = 0 → PageEmptyState (Users icon, "Загрузите участников на странице Импорта", action → /import); (3) else → render normal tabs UI.

**Checkpoint**: Messaging page shows correct tiered empty states. Tests pass.

---

## Phase 4: User Story 3 - Audience Empty States (Priority: P3)

**Goal**: Show informational empty state on GuestList page when no contacts.

**Independent Test**: Open GuestList page with empty DB — should show "Создайте мероприятие" empty state.

### Tests for User Story 3

- [ ] T013 [P] [US3] Test for GuestList empty states in `frontend/src/pages/GuestList.test.tsx`: (1) when isNoEventError → show "Создайте мероприятие" + link to /import; (2) when event exists but 0 guests → show informational "Контакты появятся автоматически" (no action button); (3) when guests exist → show normal table.

### Implementation for User Story 3

- [ ] T014 [US3] Add empty states to GuestList in `frontend/src/pages/GuestList.tsx`: before rendering content, check (1) isNoEventError → PageEmptyState (Users icon, "Создайте мероприятие на странице Импорта", action → /import); (2) guests array empty AND no search → PageEmptyState (UserSearch icon, "Пока никто не взаимодействовал с ботом", description "Контакты появятся автоматически, когда участники начнут использовать бота", no action button); (3) else → render normal table.

**Checkpoint**: GuestList page shows correct empty states. Tests pass.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all pages

- [ ] T015 Run all frontend tests: `cd frontend && npx vitest run` — verify all pass
- [ ] T016 Run quickstart.md validation: verify all 6 pages show correct empty states

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — create PageEmptyState component + tests
- **User Story 1 (Phase 2)**: Depends on Phase 1 (uses PageEmptyState component)
- **User Story 2 (Phase 3)**: Depends on Phase 1 (uses PageEmptyState component); independent of US1
- **User Story 3 (Phase 4)**: Depends on Phase 1 (uses PageEmptyState component); independent of US1/US2
- **Polish (Phase 5)**: Depends on all user stories

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation uses PageEmptyState from Phase 1
- Each page modification is independent ([P] tasks within a story)

### Parallel Opportunities

- T001 + T002 (component + tests) can run in parallel
- T003–T006 (US1 tests) can all run in parallel
- T007–T010 (US1 implementation) can all run in parallel
- US1, US2, US3 phases can run in parallel (all depend only on Phase 1)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: PageEmptyState component
2. Complete Phase 2: US1 — 4 pipeline-dependent pages
3. **VALIDATE**: All 4 pages show correct empty states

### Incremental Delivery

1. Phase 1 → Component ready
2. Phase 2 (US1) → Pipeline pages done → Test
3. Phase 3 (US2) → Messaging done → Test
4. Phase 4 (US3) → GuestList done → Test
5. Phase 5 → Polish & final validation

---

## Summary

- **Total tasks**: 16
- **US1 tasks**: 8 (T003–T010) — 4 pipeline-dependent pages
- **US2 tasks**: 2 (T011–T012) — Messaging tiered states
- **US3 tasks**: 2 (T013–T014) — GuestList informational states
- **Setup tasks**: 2 (T001–T002) — PageEmptyState component
- **Polish tasks**: 2 (T015–T016) — validation
- **Parallel opportunities**: T001‖T002, T003‖T004‖T005‖T006, T007‖T008‖T009‖T010
- **Suggested MVP scope**: Phase 1 + User Story 1 (6 tasks)
- **Format validation**: ✅ All tasks follow checklist format (checkbox, ID, labels, file paths)
