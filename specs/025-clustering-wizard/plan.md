# Implementation Plan: Clustering Wizard

**Branch**: `025-clustering-wizard` | **Date**: 2026-02-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/025-clustering-wizard/spec.md`

## Summary

Verify and enhance the existing Clustering page (Clustering.tsx) to fully match USM EPIC-005 acceptance criteria: wizard-flow (params → result → move → approve), project move between rooms, approve with confirmation dialog, Global Stepper update, and next-step hint.

## Technical Context

**Language/Version**: TypeScript 5.x (frontend), Python 3.12+ (backend)
**Primary Dependencies**: React 19, TanStack Query 5, shadcn/ui, Tailwind CSS 4
**Storage**: PostgreSQL 16 (via existing backend API)
**Testing**: Vitest + Testing Library (frontend), pytest (backend)
**Target Platform**: Web (admin panel)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Admin tool for 3-5 concurrent users, standard web responsiveness
**Constraints**: Frontend-only changes expected; backend API already exists
**Scale/Scope**: Single page refactor/enhancement

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Telegram-First | N/A | Admin panel, not bot |
| II. AI-Augmented, Human-Approved | PASS | Clustering is AI-proposed, human-approved (approve button) |
| III. Data-Driven | PASS | Works with real project data |
| IV. Pragmatic Development | PASS | Enhancing existing page, minimal changes |
| CI/CD Gate | PASS | Will run all checks locally before push |

## Project Structure

### Documentation (this feature)

```text
specs/025-clustering-wizard/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
└── tasks.md
```

### Source Code

```text
frontend/
├── src/
│   ├── pages/
│   │   └── Clustering.tsx          # Main page (enhance)
│   │   └── Clustering.test.tsx     # Tests (enhance)
│   └── lib/
│       └── api-client.ts           # API functions (already exists)
```

**Structure Decision**: Frontend-only. Backend API already complete. Clustering.tsx already exists (475 lines) — verify against USM and enhance where needed.
