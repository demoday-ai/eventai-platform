# Implementation Plan: Import Data Tabs

**Branch**: `023-import-tabs` | **Date**: 2026-02-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/023-import-tabs/spec.md`

## Summary

Refactor the DataImport page into a tabbed layout (Event/Projects/Experts/Guests) using shadcn/ui Tabs component. Add an Event creation/editing form as the first tab. Add numbered tab labels (1-4) as ordering hints. Add a backend POST endpoint for event creation. Preserve all existing import functionality without regressions.

## Technical Context

**Language/Version**: TypeScript 5.x (frontend), Python 3.12+ (backend)
**Primary Dependencies**: React 19, TanStack Query 5, shadcn/ui, Tailwind CSS 4, FastAPI, SQLAlchemy 2.0
**Storage**: PostgreSQL 16 (existing Event model: name, start_date, end_date, description)
**Testing**: Vitest + Testing Library (frontend), pytest (backend)
**Target Platform**: Web (admin panel)
**Project Type**: Web application (monorepo: backend/ + frontend/)
**Performance Goals**: Standard web app (<1s page load)
**Constraints**: Frontend-heavy change, minimal backend (1 new endpoint)
**Scale/Scope**: 1 page refactored, 1 new backend endpoint, ~5 test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Telegram-First | N/A | Admin panel feature, not Telegram bot |
| II. AI-Augmented, Human-Approved | PASS | No AI decisions involved |
| III. Data-Driven | PASS | Uses existing Event model, TDD approach |
| IV. Pragmatic Development | PASS | YAGNI — minimal changes, reuses existing code |

**GATE RESULT**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/023-import-tabs/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/admin/events.py     # ADD: POST /admin/events endpoint
│   └── schemas/admin.py        # ADD: EventCreateRequest schema
└── tests/
    └── test_admin_events.py    # ADD: tests for create event

frontend/
├── src/
│   ├── components/ui/tabs.tsx  # ADD: shadcn Tabs component
│   ├── pages/DataImport.tsx    # MODIFY: refactor to tabbed layout
│   ├── pages/DataImport.test.tsx # MODIFY: update tests for tabs
│   └── lib/api-client.ts       # ADD: createEvent function
└── package.json                # NO CHANGE (tabs is shadcn copy-paste)
```

**Structure Decision**: Web application monorepo. Backend gets 1 new POST endpoint. Frontend refactors existing DataImport page into tabs.
