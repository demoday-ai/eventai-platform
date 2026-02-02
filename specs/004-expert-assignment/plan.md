# Implementation Plan: Распределение экспертов

**Branch**: `004-expert-assignment` | **Date**: 2026-02-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-expert-assignment/spec.md`

## Summary

Автоматическое распределение 294 экспертов по тематическим комнатам Demo Day на основе совпадения тегов интересов с тематиками комнат (из утверждённой кластеризации EPIC-002). Система использует взвешенный tag-overlap алгоритм с приоритизацией редких тегов, предлагает организатору распределение для ручной корректировки, затем генерирует персональные приглашения экспертам через Telegram-бот. Дашборд покрытия показывает статус по каждой комнате с эскалацией при нехватке экспертов.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, httpx (OpenRouter), APScheduler
**Storage**: PostgreSQL 16 (asyncpg)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Yandex Cloud VM, Ubuntu 22.04)
**Project Type**: web (backend-only, Telegram bot as frontend)
**Performance Goals**: Matching 294 experts × 10 rooms < 5 sec; invite delivery < 1 sec/expert
**Constraints**: Telegram Bot API limits (30 msg/sec, 4096 chars, 64 bytes callback_data); experts must `/start` bot first; max 4 messages per expert per DD cycle
**Scale/Scope**: 294 experts, 31 tags, ~10 rooms, 1 event

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Telegram-First ✅

- Все взаимодействия эксперта (приглашение, подтверждение, смена комнаты) через Telegram-бот с inline-кнопками
- Организатор управляет матчингом и дашбордом через бот (ConversationHandler)
- Ограничения Bot API учтены: очередь отправки (30 msg/sec), callback_data < 64 bytes, пагинация для длинных списков
- Свободный текстовый ввод не используется — только кнопки

### II. AI-Augmented, Human-Approved ✅

- AI предлагает распределение (tag-overlap + LLM для смежных тегов)
- Организатор утверждает распределение и подтверждает рассылку (двухэтапно: превью → отправка)
- Эскалация молчащих экспертов — организатору, не автоматически
- CRUD-операции (подтверждения, отказы, смена комнаты) не зависят от LLM

### III. Data-Driven ✅

- Seed из реальных данных: `data/expert-mapping.json` (294 эксперта) + `data/experts-public.json` (теги, статусы)
- Комнаты из утверждённой кластеризации EPIC-002 (реальные проекты DD)
- Тестируемо на реальных масштабах (294 × 10)

### IV. Pragmatic Development ✅

- YAGNI: один эксперт — одна комната (без переходов), фиксированный порог покрытия (2), слоты — P2 (отложены)
- Предзагруженные данные для демо
- Переиспользование существующих паттернов: models (Base + UUID), services (async), bot (ConversationHandler), LLM client

**Gate result: PASS** — все 4 принципа соблюдены, нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/004-expert-assignment/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.yaml         # OpenAPI 3.0 spec
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   ├── expert.py              # Expert profile model
│   │   ├── expert_tag.py          # Expert-Tag M2M junction
│   │   ├── expert_room_assignment.py  # Expert-Room assignment
│   │   └── escalation.py          # Escalation record
│   ├── services/
│   │   ├── expert_service.py      # Expert CRUD, seed loading
│   │   ├── matching_service.py    # Tag-overlap matching algorithm
│   │   └── invite_service.py      # Invite generation, reminders, escalation
│   ├── schemas/
│   │   └── expert.py              # Pydantic schemas
│   ├── api/
│   │   └── experts.py             # REST endpoints
│   └── bot/
│       └── handlers/
│           └── expert_assignment.py  # Bot wizard for organizer + expert flows
├── alembic/
│   └── versions/
│       └── 003_expert_assignment.py  # Migration
└── data/
    └── seed/
        └── experts_seed.json      # Merged seed (mapping + tags)

scripts/
└── prepare_expert_seed.py         # Merge expert-mapping.json + experts-public.json
```

**Structure Decision**: Follows existing backend/ pattern (EPIC-001, EPIC-002). New models, services, schemas, API router, and bot handler added in parallel directories. No new top-level packages.

## Complexity Tracking

> No violations — all gates passed. No complexity tracking needed.
