# Research: Подтверждение участия студентов

**Date**: 2026-02-02

## R1: Массовая рассылка через Telegram Bot API

**Decision**: Очередь с rate limiting 25 msg/sec (запас от лимита 30)

**Rationale**: Telegram Bot API ограничивает отправку до 30 сообщений в секунду. При 330 студентах рассылка займёт ~13 секунд. Нужна очередь с задержкой, чтобы не получить 429 Too Many Requests.

**Alternatives considered**:
- Прямая отправка без задержки — рискованно, Telegram блокирует
- asyncio.sleep(0.04) между сообщениями — простейший вариант, достаточен для MVP
- Celery/Redis queue — избыточно для 330 сообщений

**Implementation**: asyncio loop с `asyncio.sleep(0.04)` между отправками. Если сообщение не доставлено (ошибка API) — логировать и добавить в список "неподключённых".

## R2: Callback data encoding для inline-кнопок

**Decision**: Формат `confirm:{request_id_short}` / `decline:{request_id_short}`

**Rationale**: Telegram ограничивает callback_data до 64 байт. UUID = 36 символов. Используем short ID (первые 8 символов UUID) + prefix. Итого: `confirm:abcd1234` = 16 байт.

**Alternatives considered**:
- Полный UUID в callback_data — 44 байта, влезает, но оставляет мало запаса
- Числовой auto-increment ID — проще, но ломает консистентность с UUID-based моделями
- Short UUID (8 chars) — достаточно уникален для ~330 записей, коллизии нереальны

## R3: Планировщик напоминаний и эскалаций

**Decision**: Background task при старте приложения (asyncio periodic task)

**Rationale**: Для MVP не нужен полноценный task scheduler. Достаточно asyncio-задачи, которая раз в час проверяет неотвеченные запросы и отправляет напоминания / эскалации.

**Alternatives considered**:
- APScheduler — добавляет зависимость, но более надёжен для продакшена
- Celery + Redis — избыточно для MVP
- Cron job — не интегрирован с приложением

**Implementation**: `asyncio.create_task()` в lifespan FastAPI. Периодическая проверка каждый час. В будущем можно мигрировать на APScheduler.

## R4: Связь ParticipationRequest с расписанием (EPIC-002)

**Decision**: FK на `room_projects` (проект в конкретном зале) + поле `proposed_time`

**Rationale**: EPIC-002 создаёт `ClusteringRun` → `Room` → `RoomProject`. Студент привязан к проекту через `Project.telegram_contact`. ParticipationRequest ссылается на `room_project_id` (какой проект в каком зале) + `proposed_time` (слот времени).

**Alternatives considered**:
- FK на project_id + room_id отдельно — денормализация
- FK только на project_id — теряем информацию о зале
- Новая таблица schedule_slots — избыточно для MVP

## R5: Ежедневная автосводка организатору

**Decision**: Тот же periodic task (R3), отдельная проверка — раз в день в 10:00

**Rationale**: Организатор получает автосводку в Telegram. Объединяем с тем же планировщиком из R3. Проверяем время: если 10:00 ± 30 мин — отправляем сводку.

**Implementation**: В periodic task добавляем проверку: если прошло >23.5 часов с последней сводки и текущее время ~10:00 — отправляем.
