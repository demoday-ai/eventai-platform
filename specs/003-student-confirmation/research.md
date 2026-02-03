# Research: Ознакомление студентов с расписанием

**Date**: 2026-02-02 (updated after clarify)

## R1: Массовая рассылка через Telegram Bot API

**Decision**: Очередь с rate limiting 25 msg/sec (запас от лимита 30)

**Rationale**: Telegram Bot API ограничивает отправку до 30 сообщений в секунду. При 330 студентах рассылка займёт ~13 секунд. Нужна очередь с задержкой, чтобы не получить 429 Too Many Requests.

**Alternatives considered**:
- Прямая отправка без задержки — рискованно, Telegram блокирует
- `asyncio.sleep(0.04)` между сообщениями — простейший вариант, достаточен для MVP
- Celery/Redis queue — избыточно для 330 сообщений

**Implementation**: asyncio loop с `asyncio.sleep(0.04)` между отправками. Если сообщение не доставлено (403 Forbidden = бот заблокирован, 400 Bad Request = невалидный chat_id) — логировать и добавить в список "неподключённых".

## R2: Callback data encoding для inline-кнопки

**Decision**: Формат `ack:{request_id_short}` (8 символов UUID)

**Rationale**: Telegram ограничивает callback_data до 64 байт. Одна кнопка "Ознакомлен" — один формат callback. UUID = 36 символов. Используем short ID (первые 8 символов UUID) + prefix. Итого: `ack:abcd1234` = 12 байт.

**Alternatives considered**:
- Полный UUID в callback_data — 40 байт, влезает, но оставляет мало запаса
- Числовой auto-increment ID — проще, но ломает консистентность с UUID-based моделями
- Short UUID (8 chars) — достаточно уникален для ~330 записей, коллизии нереальны

## R3: Планировщик напоминаний и эскалаций (DD-relative)

**Decision**: Background task при старте приложения (asyncio periodic task). Таймеры привязаны к дате DD.

**Rationale**: Для MVP не нужен полноценный task scheduler. Достаточно asyncio-задачи, которая раз в час проверяет неознакомленных студентов и рассчитывает дедлайны относительно даты DD из Event.start_date.

**Alternatives considered**:
- APScheduler — добавляет зависимость, но более надёжен для продакшена
- Celery + Redis — избыточно для MVP
- Cron job — не интегрирован с приложением

**Implementation**: `asyncio.create_task()` в lifespan FastAPI. Периодическая проверка каждый час:
- Если до DD ≤5 дней и студент не ознакомлен и напоминание не отправлено → отправить напоминание
- Если до DD ≤2 дня и студент не ознакомлен и эскалация не отправлена → эскалация организатору
- Если ~10:00 и прошло >23.5ч с последней сводки → ежедневная сводка организатору

## R4: Связь ParticipationRequest с расписанием (EPIC-002)

**Decision**: FK на `room_projects` (проект в конкретном зале). Поле `proposed_time` не нужно — время определяется по залу.

**Rationale**: EPIC-002 создаёт `ClusteringRun` → `Room` → `RoomProject`. Студент привязан к проекту через `Project.telegram_contact`. ParticipationRequest ссылается на `room_project_id` (какой проект в каком зале). Зал определяется через `Room.name` и `Room.display_order`.

**Existing models (from claude-stable)**:
- `Project` (projects): title, author, telegram_contact, event_id
- `Room` (rooms): name, display_order, clustering_run_id
- `RoomProject` (room_projects): room_id, project_id, is_manual
- `ClusteringRun` (clustering_runs): event_id, status, approved_at
- `Event` (events): name, start_date, end_date
- `User` (users): telegram_user_id, full_name, username

## R5: Ежедневная автосводка организатору

**Decision**: Тот же periodic task (R3), отдельная проверка — раз в день в 10:00

**Rationale**: Организатор получает автосводку в Telegram. Объединяем с тем же планировщиком из R3.

**Implementation**: В periodic task добавляем проверку: если прошло >23.5 часов с последней сводки и текущее время ~10:00 — отправляем. Формат: "Ознакомились: X/Y. Не ответили: Z. По залам: ..."

## R6: Идемпотентность повторной рассылки

**Decision**: При повторной рассылке — сравнить текущий room_project_id со старым. Если изменился — отправить новое сообщение с "Расписание изменено" и сбросить статус.

**Rationale**: Организатор может изменить расписание и запустить рассылку повторно. Студенты с неизменённым слотом не должны получать повторное сообщение. Студенты с изменённым слотом получают новое сообщение и должны заново нажать "Ознакомлен".

**Implementation**: При broadcast — для каждого проекта:
- Если ParticipationRequest не существует → создать и отправить
- Если существует и room_project_id не изменился → пропустить
- Если существует и room_project_id изменился → обновить room_project_id, сбросить статус на `sent`, отправить с пометкой "Расписание изменено"

## R7: Определение студента по проекту

**Decision**: Связь через `Project.telegram_contact` → `User.username` (или `User.telegram_user_id`)

**Rationale**: Проект хранит `telegram_contact` (username автора). Пользователь регистрируется в боте через EPIC-001 и получает `users.telegram_user_id`. Для рассылки: project.telegram_contact ↔ user.username → user.telegram_user_id → bot.send_message(chat_id).

**Edge case**: Если telegram_contact не совпадает ни с одним зарегистрированным пользователем — студент попадает в список "неподключённых".
