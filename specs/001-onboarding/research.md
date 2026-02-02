# Research: Онбординг и выбор роли

**Feature**: 001-onboarding
**Date**: 2026-02-02

---

## 1. python-telegram-bot: паттерн обработки онбординга

**Decision**: Использовать `ConversationHandler` из python-telegram-bot 21.x для управления состояниями онбординга.

**Rationale**: ConversationHandler — стандартный способ реализации многошагового диалога. Поддерживает per-user состояния, fallback-обработчики для невалидного ввода, вложенные состояния (роль → подтип). Версия 21.x полностью async-native.

**Alternatives considered**:
- Ручной state machine в БД — избыточно для 2-3 шагов, нарушает YAGNI
- aiogram вместо python-telegram-bot — менее зрелая экосистема, команда уже зафиксировала PTB в конституции

**Состояния ConversationHandler**:
```
CHOOSING_ROLE → (если guest) CHOOSING_SUBTYPE → END
             → (иначе) END
```

---

## 2. callback_data: кодирование в 64 байтах

**Decision**: Формат callback_data: `{action}:{value}`, например `role:student`, `subtype:ai_practitioner`.

**Rationale**: Максимум 64 байта. Самый длинный вариант: `subtype:ai_practitioner` = 24 байта — укладывается с запасом. Нет необходимости в UUID или сериализации — роли и подтипы статичны.

**Alternatives considered**:
- JSON в callback_data — тяжело, легко превысить лимит
- Числовые коды (role:1) — теряется читаемость при отладке

---

## 3. SQLAlchemy: upsert при /start

**Decision**: Использовать `INSERT ... ON CONFLICT (telegram_user_id) DO UPDATE` через `sqlalchemy.dialects.postgresql.insert` для создания/обновления пользователя при каждом /start.

**Rationale**: При повторном /start нужно обновить имя из Telegram-профиля (может измениться). Upsert атомарен, не требует SELECT+INSERT/UPDATE, безопасен при concurrent requests.

**Alternatives considered**:
- SELECT + INSERT/UPDATE в транзакции — race condition при 200 concurrent /start
- Только INSERT с игнорированием ошибки — не обновляет изменившееся имя

---

## 4. Whitelist организаторов

**Decision**: Whitelist Telegram ID организаторов — переменная окружения `ORGANIZER_TELEGRAM_IDS` (comma-separated). Парсится при старте приложения в `set[str]`.

**Rationale**: Для демо достаточно env var (~5 ID). Не требует UI или БД-таблицы. Изменение — перезапуск бота (допустимо при 5 организаторах).

**Alternatives considered**:
- Таблица в БД с UI управления — overengineering для MVP с 5 организаторами
- Role invites (ER: role_invites) — предусмотрено в ER, но для Release 1.1

---

## 5. Архитектура: бот + API в одном процессе

**Decision**: Telegram-бот и FastAPI API запускаются в одном Python-процессе через общий asyncio event loop. Бот работает в webhook-режиме (FastAPI принимает webhook от Telegram).

**Rationale**: Одна VM с 4 vCPU — разделение на два процесса не даёт преимуществ. Webhook-режим эффективнее polling: не тратит ресурсы на long-polling, работает за Traefik reverse proxy. Общая SQLAlchemy-сессия упрощает код.

**Alternatives considered**:
- Polling-режим — проще для разработки, но не работает за NAT/proxy кэмпа без дополнительных настроек
- Отдельные процессы бот + API — сложнее деплой, нет выгоды на одной VM
- Polling для dev, webhook для prod — допустимо, реализуем через конфиг `BOT_MODE=webhook|polling`

---

## 6. Seed-данные для демо

**Decision**: Alembic migration с seed-данными: 5 ролей, 1 событие (Demo Day 2026-02-06). Организаторские ID из env var.

**Rationale**: Конституция: "Предзагруженные данные для демо." Seed в миграции гарантирует наличие данных в любом окружении.

**Alternatives considered**:
- Ручной SQL-скрипт — может быть забыт при деплое
- Fixtures в тестах — не попадают в production
