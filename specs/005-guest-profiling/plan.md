# Implementation Plan: Профилирование и программа для гостей (EPIC-005)

**Branch**: `005-guest-profiling` | **Date**: 2026-02-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-guest-profiling/spec.md`

## Summary

Реализовать гибридное профилирование интересов гостей (inline-кнопки + свободный текст) в Telegram-боте и генерацию персональной программы из 10-15 проектов. Ранжирование: IDF-взвешенный tag overlap для отбора кандидатов → LLM re-ranking top-20 с учётом свободного текста профиля → LLM-генерация кратких описаний адаптированных под гостя. Graceful degradation при недоступности LLM.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, httpx (OpenRouter)
**Storage**: PostgreSQL 16 (async via asyncpg)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Yandex Cloud VM, 4 vCPU, 8GB RAM)
**Project Type**: Web application (backend-only, Telegram bot as client)
**Performance Goals**: Генерация программы ≤10 секунд (SC-002), профилирование ≤2 минуты (SC-001)
**Constraints**: Telegram Bot API: 4096 символов/сообщение, 64 байта callback data, 30 msg/sec
**Scale/Scope**: ~50 гостей, ~330 проектов, ~31 тег

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Telegram-First** | ✅ PASS | Все взаимодействие через Telegram-бот: inline-кнопки для тегов, свободный текст для профиля, inline для навигации по подборке |
| **II. AI-Augmented, Human-Approved** | ✅ PASS | AI извлекает интересы из текста и ранжирует проекты, гость подтверждает профиль перед сохранением. Q&A-подсказки для гостей только (не экспертов). Graceful degradation при недоступности LLM |
| **III. Data-Driven** | ✅ PASS | Используются реальные данные: 333 проекта, 31 тег из seed data. IDF-веса из existing tag distribution |
| **IV. Pragmatic Development** | ✅ PASS | Минимум новых сущностей (2 таблицы). Переиспользуется: llm_client, Tag система, matching IDF-формула. Предзагруженные данные для демо |

**Gate result: PASS** — все 4 принципа соблюдены.

## Project Structure

### Documentation (this feature)

```text
specs/005-guest-profiling/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── guest-profiling-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/
│   └── 004_guest_profiling.py          # New migration
├── app/
│   ├── models/
│   │   ├── guest_profile.py            # NEW: GuestProfile model
│   │   ├── recommendation.py           # NEW: Recommendation model
│   │   └── __init__.py                 # Updated: register new models
│   ├── services/
│   │   ├── profiling_service.py        # NEW: profiling + recommendation logic
│   │   └── llm_client.py              # Existing: reused for text extraction + re-ranking
│   ├── api/
│   │   └── guests.py                   # NEW: REST endpoints for guest profiling
│   ├── bot/
│   │   ├── handlers/
│   │   │   ├── guest_profiling.py      # NEW: ConversationHandler for profiling flow
│   │   │   └── start.py               # Modified: auto-trigger profiling after onboarding
│   │   ├── keyboards.py               # Modified: add profiling keyboards
│   │   └── app.py                     # Modified: register new handler
│   └── main.py                        # Modified: register new API router
└── tests/
    └── test_profiling_service.py       # NEW: unit tests
```

**Structure Decision**: Extends existing backend-only structure. No frontend. 2 new models, 1 new service, 1 new bot handler, 1 new API router. Follows established patterns from EPIC-002/003/004.

## Complexity Tracking

> No violations. Feature uses existing patterns and minimal new abstractions.
