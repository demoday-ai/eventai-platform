# Implementation Plan: DD Reminders & Timing Shift Notifications

**Branch**: `005-dd-reminders` | **Date**: 2026-02-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-dd-reminders/spec.md`

## Summary

Автоматические напоминания участникам Demo Day (студенты, эксперты, гости, бизнес-партнёры) и уведомления при сдвигах расписания. Система генерирует расписание из утверждённой кластеризации (авто-слоты, равномерное распределение по комнатам), отправляет персонализированные напоминания накануне DD (18:00 MSK) и за 1 час до слота, а также мгновенно уведомляет участников при переносе проектов. Организатор может просматривать и отменять рассылку, видит дашборд доставки. Все уведомления через Telegram Bot API с throttling (30 msg/sec) и retry (3 попытки).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, APScheduler 3.10+
**Storage**: PostgreSQL 16 (asyncpg)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Yandex Cloud VM, Ubuntu 22.04)
**Project Type**: web (backend-only, Telegram bot as frontend)
**Performance Goals**: Eve-of-DD send for ~500 participants < 20 sec (throttled at 30 msg/sec); pre-slot reminder check every 5 min; timing shift notification < 2 min after schedule change
**Constraints**: Telegram Bot API (30 msg/sec, 4096 chars/msg, 64 bytes callback_data); Moscow time (UTC+3); no email/SMS
**Scale/Scope**: ~330 projects, ~400 participants (students + experts + guests), 6-10 rooms, 2-day event

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Telegram-First ✅

- Все уведомления отправляются через Telegram Bot API (`bot.send_message`)
- Организатор управляет расписанием и дашбордом через inline-кнопки в боте
- Ограничения Bot API учтены: throttling при массовой отправке (30 msg/sec), пагинация для длинных списков, callback_data < 64 bytes
- Свободный текстовый ввод не используется — только кнопки и автоматические сообщения

### II. AI-Augmented, Human-Approved ✅

- Расписание авто-генерируется, но организатор утверждает перед рассылкой
- Рассылка гибридная: авто-отправка в 18:00, но организатор может отменить до 17:00 (1 час preview)
- Напоминалки — CRUD-функции, НЕ зависят от LLM (graceful degradation OK)
- Уведомления о сдвигах — автоматические, но инициируются действием организатора (изменение расписания)

### III. Data-Driven ✅

- Расписание генерируется из реальных данных кластеризации (EPIC-002: ~330 проектов, 6-10 комнат)
- Тестируемо на реальных масштабах (seed data: 400 проектов, 294 эксперта)
- Все notification records логируются в БД — аналитика доставки для организатора

### IV. Pragmatic Development ✅

- YAGNI: один формат слота (15 мин), нет пользовательских настроек тайминга, нет email fallback
- Переиспользование паттернов: APScheduler (из EPIC-004), Escalation model (из EPIC-004), bot handlers (ConversationHandler), services (async)
- Предзагруженные данные: расписание авто-генерируется из существующего seed
- Минимум новых зависимостей: нет (APScheduler уже установлен)

**Gate result: PASS** — все 4 принципа соблюдены, нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/005-dd-reminders/
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
│   │   ├── schedule_slot.py          # Schedule slot (project × room × time)
│   │   ├── notification.py           # Notification record (sent/failed/pending)
│   │   └── schedule_change_log.py    # Audit trail for schedule modifications
│   ├── services/
│   │   ├── schedule_service.py       # Schedule generation, slot CRUD, change detection
│   │   └── notification_service.py   # Reminder scheduling, sending, batching, retry
│   ├── schemas/
│   │   └── schedule.py               # Pydantic schemas for schedule + notifications
│   ├── api/
│   │   └── schedule.py               # REST endpoints for schedule management
│   └── bot/
│       └── handlers/
│           └── schedule.py           # Bot commands: /schedule, /reminders, organizer dashboard
├── alembic/
│   └── versions/
│       └── 004_dd_reminders.py       # Migration: schedule_slots, notifications, schedule_change_logs
```

**Structure Decision**: Follows existing backend/ pattern (EPIC-001 through EPIC-004). New models, services, schemas, API router, and bot handler added in parallel directories. No new top-level packages. Extends existing APScheduler jobs in `main.py`.

## Complexity Tracking

> No violations — all gates passed. No complexity tracking needed.
