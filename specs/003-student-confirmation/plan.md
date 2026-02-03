# Implementation Plan: Ознакомление студентов с расписанием

**Branch**: `003-student-confirmation` | **Date**: 2026-02-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-student-confirmation/spec.md`

## Summary

Система рассылки персональных слотов студентам с подтверждением ознакомления через Telegram-бота. Организатор запускает рассылку командой, студенты подтверждают одной кнопкой "Ознакомлен" (участие обязательное, отказа нет), неознакомленные эскалируются автоматически по таймерам, привязанным к дате DD. Организатор видит сводку и получает ежедневный автоотчёт.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, asyncpg
**Storage**: PostgreSQL 16
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Yandex Cloud VM, 4 vCPU, 8GB RAM)
**Project Type**: Web (backend + Telegram bot)
**Performance Goals**: Рассылка 330 сообщений за <15 сек (rate limit 25 msg/sec с запасом)
**Constraints**: Telegram Bot API: 30 msg/sec, 4096 chars/msg, 64 bytes callback_data
**Scale/Scope**: ~330 студентов, ~5 организаторов, 1 событие

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Telegram-First | PASS | Все взаимодействия через inline-кнопку "Ознакомлен" в Telegram. Свободный текст не используется |
| II. AI-Augmented, Human-Approved | PASS | Организатор явно запускает рассылку. Фича — CRUD, не зависит от LLM. При недоступности LLM — работает без ограничений |
| III. Data-Driven | PASS | Данные из EPIC-002 (кластеризация → room_projects), проекты из формы контрольного рубежа |
| IV. Pragmatic Development | PASS | RICE 495 (2-й приоритет). Минимум абстракций: новая модель + handler + service. Один статус-флоу (pending→sent→acknowledged) |

## Project Structure

### Documentation (this feature)

```text
specs/003-student-confirmation/
├── plan.md              # This file
├── spec.md              # Feature specification (clarified)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.yaml         # OpenAPI spec
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   └── participation.py          # ParticipationRequest model
│   ├── schemas/
│   │   └── participation.py          # Request/response schemas
│   ├── services/
│   │   └── participation_service.py  # Business logic (broadcast, acknowledge, escalation)
│   ├── api/
│   │   └── participation.py          # REST endpoints (organizer dashboard)
│   └── bot/
│       └── handlers/
│           └── confirmation.py       # Student acknowledgment handler + organizer commands
├── alembic/
│   └── versions/
│       └── 005_participation_requests.py  # Migration
└── tests/
    └── test_participation.py             # Tests
```

**Structure Decision**: Follows existing pattern from EPIC-001/002/004/005 — model + schema + service + api + bot handler. No new directories needed beyond existing structure.

## Complexity Tracking

No constitution violations. No complexity justification needed.
