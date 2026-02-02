# Implementation Plan: Загрузка и AI-кластеризация проектов

**Branch**: `002-project-clustering` | **Date**: 2026-02-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-project-clustering/spec.md`

## Summary

Организатор загружает данные о проектах (CSV/JSON) через Telegram-бот, запускает AI-кластеризацию по тематическим залам, корректирует результат и утверждает расписание. Система использует LLM (OpenRouter API через Xray proxy) для семантической кластеризации по описаниям и тегам с балансировкой залов. Предзагруженные seed-данные из checkpoint-форм (~305 проектов) обеспечивают демо 6 февраля.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, asyncpg, httpx (OpenRouter API)
**Storage**: PostgreSQL 16
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Yandex Cloud VM: 4 vCPU, 8GB RAM)
**Project Type**: Web application (backend-only, Telegram bot as frontend)
**Performance Goals**: Кластеризация 305 проектов < 120 сек (SC-001). Inline-кнопки < 1 сек (NFR 1.3).
**Constraints**: Telegram Bot API — 30 msg/sec, 4096 символов/сообщение, 64 байта callback_data. LLM rate limits OpenRouter.
**Scale/Scope**: ~305 проектов, 6 залов, ~5 организаторов. Событийная нагрузка.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Telegram-First | **PASS** | Весь workflow через бот: загрузка файла, inline-кнопки wizard, просмотр результатов |
| II | AI-Augmented, Human-Approved | **PASS** | AI кластеризует, организатор корректирует и утверждает. NL-фидбэк для перегенерации |
| III | Data-Driven | **PASS** | Seed из checkpoint-форм (~305 реальных проектов). Кластеризация по тематикам, не по трекам |
| IV | Pragmatic Development | **PASS** | Расширяет существующий backend (EPIC-001). Минимум новых зависимостей (httpx для LLM). YAGNI |

## Project Structure

### Documentation (this feature)

```text
specs/002-project-clustering/
├── plan.md              # This file
├── research.md          # Phase 0: решения по кластеризации, seed-данных, UX
├── data-model.md        # Phase 1: новые таблицы и связи
├── quickstart.md        # Phase 1: инструкции запуска
├── contracts/           # Phase 1: OpenAPI-контракты
│   └── clustering-api.yaml
└── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/
│   └── 002_projects_clustering.py   # Миграция: projects, tags, rooms, clustering_runs
├── app/
│   ├── models/
│   │   ├── project.py               # Project model
│   │   ├── tag.py                    # Tag model
│   │   ├── project_tag.py           # M2M junction
│   │   ├── room.py                  # Room model (результат кластеризации)
│   │   └── clustering_run.py        # Clustering run (параметры, статус)
│   ├── schemas/
│   │   └── project.py               # Pydantic schemas: ProjectUpload, ClusteringResult, etc.
│   ├── services/
│   │   ├── project_service.py       # CRUD проектов, парсинг CSV/JSON, валидация
│   │   ├── clustering_service.py    # Кластеризация: LLM-вызов, балансировка, NL-фидбэк
│   │   └── seed_service.py          # Загрузка seed-данных из checkpoint12
│   ├── api/
│   │   └── projects.py              # REST: upload, cluster, move, approve
│   └── bot/
│       ├── handlers/
│       │   └── clustering.py        # ConversationHandler: wizard загрузка→кластер→корректировка→утверждение
│       └── keyboards.py             # + новые клавиатуры для кластеризации
├── data/
│   └── seed/
│       └── projects_seed.json       # Предпарсенные seed-данные из checkpoint12 + теги
└── tests/
    ├── unit/
    │   ├── test_project_service.py
    │   └── test_clustering_service.py
    └── integration/
        └── test_clustering_flow.py
```

**Structure Decision**: Расширяем существующую структуру backend/ из EPIC-001. Новые модели, сервисы и handlers добавляются в существующие директории. Seed-данные — в `data/seed/`.

## Complexity Tracking

> No Constitution violations — table empty.
