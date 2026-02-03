# Implementation Plan: DD Reminders Polish (EPIC-007b)

**Branch**: `007b-dd-reminders-polish` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/007b-dd-reminders-polish/spec.md`
**Parent**: EPIC-007 (DD Reminders)

## Summary

Доработки и полировка EPIC-007: защита от превышения лимита Telegram (4096 символов) через обрезку списка проектов, восстановление прерванных рассылок, E2E валидация сценариев.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, asyncpg
**Storage**: PostgreSQL 16
**Testing**: pytest + pytest-asyncio (manual validation via bot)
**Target Platform**: Linux server (Yandex Cloud VM)
**Project Type**: Single (monorepo backend/)
**Performance Goals**: Truncation <10ms, batch recovery detection <1s
**Constraints**: Telegram 4096 char limit, safe threshold 4000 chars
**Scale/Scope**: ~400 recipients, messages up to 50 projects per guest

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. Telegram-First | Respects 4096 char limit, uses inline buttons for recovery | ✅ PASS |
| II. AI-Augmented, Human-Approved | Organizer decides on batch recovery/cancel | ✅ PASS |
| III. Data-Driven | Uses existing notification status for deduplication | ✅ PASS |
| IV. Pragmatic Development | Completes EPIC-007, minimal new code | ✅ PASS |

## Project Structure

### Documentation (this feature)

```text
specs/007b-dd-reminders-polish/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (N/A - no new entities)
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   └── reminder_service.py   # MODIFY: add truncation, recovery logic
│   └── bot/
│       ├── handlers/
│       │   └── reminder.py       # MODIFY: add recovery flow to /remind
│       └── keyboards.py          # MODIFY: add recovery keyboards
└── tests/
    └── e2e/
        └── test_reminders.py     # NEW: E2E validation scenarios
```

**Structure Decision**: No new files. Modifications to existing reminder_service.py, reminder.py handler, and keyboards.py from EPIC-007.

## Complexity Tracking

> No Constitution Check violations. All principles satisfied.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Truncation | In-service helper function | Simple string manipulation, no new abstraction needed |
| Batch recovery | Query + keyboard flow | Reuses existing keyboard patterns from EPIC-006/007 |
| E2E tests | Manual + quickstart.md | Time constraint, manual validation sufficient for demo |
