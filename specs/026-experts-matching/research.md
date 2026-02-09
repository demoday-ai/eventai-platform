# Research: Experts Matching, List & Coverage

**Phase 0 — Resolve unknowns**

## R1: Current Implementation State

**Decision**: Page is 95% implemented. Only 3 gaps to close.

**Analysis of existing files**:
- `ExpertMatching.tsx` (599 lines): Full wizard with 3 steps (run → results/move/assign → approve/invites). Missing: confirmation dialog, next-step hint, pipeline invalidation.
- `ExpertList.tsx` (189 lines): Full CRUD table with search, filters, status badges, confirm/decline buttons. Fully complete.
- `Coverage.tsx` (310 lines): 3 tabs (Overview, Gaps, Escalations) with room table, gap cards, escalation table. Fully complete.
- `CoverageRoomDetail.tsx` (158 lines): Room detail page with experts, uncovered tags, candidates. Fully complete.
- `ExpertFormDialog` component exists for create/edit.

**Gaps found** (same pattern as EPIC-005 Clustering):
1. No confirmation dialog before approveMatching — approves directly
2. No next-step hint after approval ("Следующий шаг — генерация расписания" + link to /schedule)
3. No pipeline-status and dashboard query invalidation after approve

## R2: Test Coverage

**Decision**: Existing tests cover core flows. Need 2-3 additional tests for new features.

**Current tests**:
- `ExpertMatching.test.tsx`: 5 tests (empty state, run step, results, scores, error)
- `ExpertList.test.tsx`: 8 tests (CRUD, search, status badges, validation)
- `Coverage.test.tsx`: 5 tests (summary, gaps, escalations, error, details button)
- `CoverageRoomDetail.test.tsx`: exists

**Tests needed**:
- Confirmation dialog on approve click
- Next-step hint after approval
- Pipeline-status invalidation (verify queryClient call)

## R3: API Endpoints

**Decision**: All required backend endpoints exist. No changes needed.

All API functions already exist in api-client.ts: runMatching, getCurrentMatching, moveExpert, assignExpert, approveMatching, getInvitePreview, confirmInvites, getExperts, getCoverageSummary, getCoverageGaps, getEscalations, resolveEscalation, getRoomCoverageDetail.
