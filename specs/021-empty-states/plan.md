# Implementation Plan: Empty States и подсказки

**Branch**: `021-empty-states` | **Date**: 2026-02-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/021-empty-states/spec.md`

## Summary

Add consistent empty states to all admin panel pages that depend on pipeline steps (projects, clustering, matching, schedule) or data availability (messaging participants, audience contacts). Reuse and extend the existing `EmptyState` component to accept configurable icon, title, description, and action link. Frontend-only feature — no backend changes needed.

## Technical Context

**Language/Version**: TypeScript 5.x (React 19)
**Primary Dependencies**: React 19, React Router v7, TanStack Query 5, shadcn/ui, Lucide React
**Storage**: N/A (frontend-only; reads existing API data)
**Testing**: Vitest + @testing-library/react
**Target Platform**: Web (modern browsers)
**Project Type**: Web application (monorepo: backend/ + frontend/)
**Performance Goals**: Empty state renders instantly; no additional API calls beyond existing queries
**Constraints**: Reuse existing EmptyState component pattern; follow USM visual principles (minimalism, Lucide icons, functional color)
**Scale/Scope**: 6 pages to update (ProjectsList, Clustering, ExpertMatching, Schedule, Messaging, GuestList)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | N/A | Frontend-only; no backend changes |
| II. Async-First | PASS | Uses existing TanStack Query async data flow |
| III. Test-Driven Development | PASS | Tests for each page's empty state; min 80% coverage |
| IV. Monorepo Conventions | PASS | All changes in frontend/src/; no cross-boundary changes |
| V. AI-First Product | N/A | No LLM integration |
| VI. Data Privacy | N/A | No user data handling |
| VII. Simplicity & YAGNI | PASS | Extending one existing component; minimal changes per page |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/021-empty-states/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal — frontend-only)
├── quickstart.md        # Phase 1 output
├── contracts/           # N/A (no new API endpoints)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   └── ui/
│   │       └── PageEmptyState.tsx     # New: reusable empty state component
│   ├── pages/
│   │   ├── ProjectsList.tsx           # Modified: add empty state for no projects
│   │   ├── Clustering.tsx             # Modified: add empty state for no projects
│   │   ├── ExpertMatching.tsx         # Modified: add empty state for no approved clustering
│   │   ├── Schedule.tsx               # Modified: add empty state for no approved clustering
│   │   ├── Messaging.tsx              # Modified: add tiered empty states
│   │   └── GuestList.tsx              # Modified: improve empty state messages
│   └── lib/
│       └── api-client.ts              # No changes needed
└── src/
    └── components/
        └── ui/
            └── PageEmptyState.test.tsx # New: tests for component
```

**Structure Decision**: Web application structure (frontend/ only). The existing `EmptyState` in `components/dashboard/` is Dashboard-specific. A new generic `PageEmptyState` in `components/ui/` will be the reusable component for all pages.

## Complexity Tracking

> No violations — table empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
