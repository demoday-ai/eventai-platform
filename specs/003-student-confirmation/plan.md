# Implementation Plan: Подтверждение участия студентов

**Branch**: `003-student-confirmation` | **Date**: 2026-02-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-student-confirmation/spec.md`

## Summary

Система рассылки персональных слотов студентам с подтверждением участия через Telegram-бота. Организатор запускает рассылку командой, студенты подтверждают одной кнопкой, неответившие эскалируются автоматически. Организатор видит сводку и получает ежедневный автоотчёт.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, asyncpg
**Storage**: PostgreSQL 16
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Yandex Cloud VM, 4 vCPU, 8GB RAM)
**Project Type**: Web (backend + Telegram bot)
**Performance Goals**: Рассылка 330 сообщений за <5 мин (лимит Telegram: 30 msg/sec)
**Constraints**: Telegram Bot API: 30 msg/sec, 4096 chars/msg, 64 bytes callback_data
**Scale/Scope**: ~330 студентов, ~5 организаторов, 1 событие

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Telegram-First | PASS | Все взаимодействия через inline-кнопки в Telegram. Свободный текст только для причины отказа |
| II. AI-Augmented, Human-Approved | PASS | Организатор явно запускает рассылку. Эта фича — CRUD, не зависит от LLM |
| III. Data-Driven | PASS | Данные из EPIC-002 (кластеризация), проекты из формы контрольного рубежа |
| IV. Pragmatic Development | PASS | RICE 495 (2-й приоритет). Минимум абстракций: новые модели + handler + service |

## Project Structure

### Documentation (this feature)

```text
specs/003-student-confirmation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.yaml         # OpenAPI spec
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   └── participation.py       # ParticipationRequest model
│   ├── schemas/
│   │   └── participation.py       # Request/response schemas
│   ├── services/
│   │   └── participation_service.py  # Business logic
│   ├── api/
│   │   └── participation.py       # REST endpoints (organizer)
│   └── bot/
│       └── handlers/
│           └── confirmation.py    # Student confirmation handler
├── alembic/
│   └── versions/
│       └── 003_participation_requests.py  # Migration
└── tests/
    └── test_participation.py      # Tests
```

**Structure Decision**: Follows existing pattern from EPIC-001/002 — model + schema + service + api + bot handler. No new directories needed beyond existing structure.
