# Tasks: Experts Matching

**Input**: Design documents from `/specs/026-experts-matching/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅

**Organization**: Minimal changes — pages are 95% implemented. Only 3 gaps to close.

## Phase 1: US2 — Confirmation Dialog + Next-Step Hint (Priority: P1)

**Goal**: Add confirmation before approve + next-step hint after approval + pipeline invalidation

- [ ] T001 [US2] Add confirmation state to approve step in `frontend/src/pages/ExpertMatching.tsx` — when "Одобрить матчинг" clicked, show "Вы уверены?" with "Подтвердить" and "Отмена" buttons instead. Only call approveMutation on "Подтвердить".
- [ ] T002 [US2] Add next-step hint after approval in `frontend/src/pages/ExpertMatching.tsx` — when approveMutation.isSuccess, show Card with message "Матчинг одобрен. Следующий шаг — генерация расписания" and a link button to /schedule.
- [ ] T003 [US2] Add pipeline-status invalidation in `frontend/src/pages/ExpertMatching.tsx` — after successful approve, call `queryClient.invalidateQueries({ queryKey: ["pipeline-status"] })` and `queryClient.invalidateQueries({ queryKey: ["dashboard"] })`.

## Phase 2: Tests

- [ ] T004 Update `frontend/src/pages/ExpertMatching.test.tsx` — add tests for: confirmation dialog appears on approve click, next-step hint shows after approval, pipeline-status invalidation.

## Phase 3: CI

- [ ] T005 Run full CI: frontend tests + eslint + tsc, backend ruff

---

## Dependencies

- T001, T002, T003 are independent (different parts of the approve step)
- T004 depends on T001-T003
- T005 depends on T004

Total: 5 tasks
