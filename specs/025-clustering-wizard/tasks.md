# Tasks: Clustering Wizard

**Input**: Design documents from `/specs/025-clustering-wizard/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅

**Organization**: Minimal changes — page is 90% implemented. Only 3 gaps to close.

## Phase 1: US3 — Confirmation Dialog + Next-Step Hint (Priority: P1)

**Goal**: Add confirmation before approve + next-step hint after approval + pipeline invalidation

- [ ] T001 [US3] Add confirmation state to approve step in `frontend/src/pages/Clustering.tsx` — when "Одобрить" clicked, show "Вы уверены?" with "Подтвердить" and "Отмена" buttons instead. Only call approveMutation on "Подтвердить".
- [ ] T002 [US3] Add next-step hint after approval in `frontend/src/pages/Clustering.tsx` — when isApproved, show Card with message "Кластеризация одобрена. Следующий шаг — распределение экспертов" and a link button to /experts.
- [ ] T003 [US3] Add pipeline-status invalidation in `frontend/src/pages/Clustering.tsx` — after successful approve, call `queryClient.invalidateQueries({ queryKey: ["pipeline-status"] })`.

## Phase 2: Tests

- [ ] T004 Update `frontend/src/pages/Clustering.test.tsx` — add tests for: confirmation dialog appears on approve click, next-step hint shows after approval, pipeline-status invalidation.

## Phase 3: CI

- [ ] T005 Run full CI: frontend tests + eslint + tsc, backend ruff

---

## Dependencies

- T001, T002, T003 are independent (different parts of the approve step)
- T004 depends on T001-T003
- T005 depends on T004

Total: 5 tasks
