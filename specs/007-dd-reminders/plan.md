# Implementation Plan: Напоминания перед Demo Day (EPIC-007)

**Branch**: `007-dd-reminders` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/007-dd-reminders/spec.md`

## Summary

Система автоматических напоминаний всем 5 ролям перед Demo Day: «за день» и «за час» до события. Организатор запускает рассылку командой `/remind`, видит превью и отчёт. Расширяет существующую инфраструктуру напоминаний (EPIC-003/004) новым слоем pre-DD уведомлений.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, asyncpg
**Storage**: PostgreSQL 16
**Testing**: pytest + pytest-asyncio (manual validation via bot + API)
**Target Platform**: Linux server (Yandex Cloud VM)
**Project Type**: Single (monorepo backend/)
**Performance Goals**: <3 min for 400 recipients (SC-004), rate limit 30 msg/sec
**Constraints**: Telegram 4096 char limit, 64 byte callback data, 0.04s delay between messages
**Scale/Scope**: ~400 recipients (330 students + 50 experts + 15 business + 5 organizers)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. Telegram-First | Bot-only interface, `/remind` command, inline buttons for confirm | ✅ PASS |
| II. AI-Augmented, Human-Approved | Organizer approves before send, preview counts, no LLM dependency | ✅ PASS |
| III. Data-Driven | Uses existing participation/expert data, logs send results | ✅ PASS |
| IV. Pragmatic Development | RICE 780 (highest priority), extends existing remind infrastructure | ✅ PASS |

## Project Structure

### Documentation (this feature)

```text
specs/007-dd-reminders/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   └── reminder.py           # NEW: ReminderBatch, Notification models
│   ├── schemas/
│   │   └── reminder.py           # NEW: Pydantic schemas
│   ├── services/
│   │   └── reminder_service.py   # NEW: Core reminder logic
│   ├── bot/
│   │   ├── handlers/
│   │   │   └── reminder.py       # NEW: /remind command handler
│   │   └── keyboards.py          # EXTEND: reminder keyboards
│   └── api/
│       └── reminders.py          # NEW: REST API for reminder status
└── alembic/
    └── versions/
        └── xxx_add_reminder_tables.py  # NEW: Migration
```

**Structure Decision**: Single project structure. New files for reminder-specific logic, extending existing patterns from EPIC-003 (participation_service) and EPIC-004 (invite_service).

## Complexity Tracking

> No Constitution Check violations. All principles satisfied.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| New tables vs extend | New `reminder_batches` + `notifications` tables | Clean separation from existing reminder fields (reminder_sent_at, escalated_at which have different semantics) |
| Service layer | New `reminder_service.py` | Dedicated logic for DD-1d/1h reminders, distinct from existing check_and_send_reminders (3-day threshold) |
| Rate limiting | Reuse 0.04s delay pattern | Already proven in participation_service.broadcast_slots |
