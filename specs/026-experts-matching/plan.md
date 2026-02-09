# Implementation Plan: Experts Matching, List & Coverage

**Input**: spec.md, research.md
**Branch**: `026-experts-matching`

## Technical Context

- **ExpertMatching.tsx**: 599 lines, nearly complete wizard. Missing: confirmation dialog, next-step hint, pipeline invalidation.
- **ExpertList.tsx**: 189 lines, fully complete (CRUD, search, status badges).
- **Coverage.tsx**: 310 lines, fully complete (overview, gaps, escalations).
- **CoverageRoomDetail.tsx**: 158 lines, fully complete (room detail, candidates).
- **Tests**: 18 existing tests across 4 test files.

## Constitution Check

- **Principle I (User Value)**: Confirmation dialog prevents accidental approval. Next-step hint improves workflow continuity.
- **Principle II (Quality)**: Pipeline invalidation ensures data consistency across pages.
- **Principle III (TDD)**: New tests for confirmation dialog and next-step hint.
- **Principle IV (Simplicity)**: Minimal changes — only 3 gaps to close.

## Implementation Strategy

Same pattern as EPIC-005 (Clustering Wizard):
1. Add confirmation state + dialog to approve step in ExpertMatching.tsx
2. Add next-step hint after approval (link to /schedule)
3. Add pipeline-status + dashboard invalidation after approve
4. Update tests

## Scope

- Frontend only — no backend changes
- 1 file to modify: `ExpertMatching.tsx`
- 1 test file to update: `ExpertMatching.test.tsx`

## Generated Artifacts

- [x] research.md
- [x] data-model.md
- [x] contracts/api.md
- [x] plan.md (this file)
