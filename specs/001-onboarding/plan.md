# Implementation Plan: Онбординг и выбор роли

**Branch**: `001-onboarding` | **Date**: 2026-02-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-onboarding/spec.md`

## Summary

Реализовать онбординг — первую точку входа в Telegram-бот. Пользователь отправляет `/start`, выбирает роль из 5 (inline-кнопки), при роли "Гость" — выбирает подтип. Данные сохраняются в PostgreSQL. Повторный `/start` и `/role` позволяют сменить роль. Роль "Организатор" защищена whitelist по Telegram ID.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, asyncpg
**Storage**: PostgreSQL 16
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux (Ubuntu 22.04, Yandex Cloud VM)
**Project Type**: Web application (backend API + Telegram bot)
**Performance Goals**: 200 concurrent sessions, <2s response на inline-кнопки
**Constraints**: Telegram callback_data ≤64 байт, 30 msg/sec rate limit, VM 4 vCPU / 8GB RAM
**Scale/Scope**: 435 пользователей, 1 событие, 5 ролей, 3 подтипа гостей

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Обоснование |
|---------|--------|-------------|
| I. Telegram-First | ✅ PASS | Только Telegram Bot API, inline-кнопки для выбора роли, нет внешних приложений |
| II. AI-Augmented, Human-Approved | ✅ PASS | Фича не использует AI. Чистый CRUD. Организатор защищён whitelist |
| III. Data-Driven | ✅ PASS | Seed-данные для демо (5 ролей, 1 событие). Анонимизация не затронута |
| IV. Pragmatic Development | ✅ PASS | Минимальная реализация: 3 user stories, 10 FR, YAGNI. Меню ролей — заглушки |

**Нарушений нет. GATE пройден.**

## Project Structure

### Documentation (this feature)

```text
specs/001-onboarding/
├── plan.md              # Этот файл
├── research.md          # Phase 0: исследование
├── data-model.md        # Phase 1: модель данных
├── quickstart.md        # Phase 1: быстрый старт
├── contracts/           # Phase 1: API-контракты
│   └── openapi.yaml
└── tasks.md             # Phase 2: задачи (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan
│   ├── config.py            # Pydantic Settings (env vars)
│   ├── database.py          # SQLAlchemy async engine + session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py          # DeclarativeBase
│   │   ├── user.py          # User model
│   │   ├── role.py          # Role model
│   │   ├── user_role.py     # UserRole model
│   │   └── event.py         # Event model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py          # Pydantic schemas
│   ├── api/
│   │   ├── __init__.py
│   │   └── auth.py          # POST /auth/login, GET /auth/me
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py  # create/get/update user + role
│   └── bot/
│       ├── __init__.py
│       ├── app.py           # Application (python-telegram-bot)
│       ├── handlers/
│       │   ├── __init__.py
│       │   ├── start.py     # /start handler
│       │   └── role.py      # /role handler, callback handlers
│       └── keyboards.py     # InlineKeyboardMarkup factories
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
├── tests/
│   ├── conftest.py
│   ├── test_start.py
│   └── test_role.py
├── pyproject.toml
├── Dockerfile
└── .env.example

docker-compose.yml          # PostgreSQL + backend
```

**Structure Decision**: Web application (backend). Telegram-бот встроен в backend как отдельный модуль `app/bot/`. Frontend (Admin Console) не нужен для этой фичи.

## Complexity Tracking

> Нарушений Constitution Check нет. Таблица пуста.
