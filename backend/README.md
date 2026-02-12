# Backend Architecture

Техническая документация backend EventAI — AI-платформы для организаторов конференций.

## Стек

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.12+ |
| Web-фреймворк | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| БД | PostgreSQL 16 (asyncpg) |
| Миграции | Alembic |
| Telegram-бот | python-telegram-bot 21.x |
| LLM | OpenRouter API (GPT-4.1) |
| Эмбеддинги | Google Gemini Embedding → Qdrant |
| Очередь задач | Celery + RabbitMQ |
| Кэш | Redis |
| Планировщик | APScheduler |
| Валидация | Pydantic v2 |
| Аутентификация | JWT (HS256) |

## Архитектура

Layered Architecture: **Routes → Services → Repos → Models**.

```
app/
├── main.py                  App factory, CORS, router includes, health
├── lifespan.py              Startup/shutdown: DB, bot, scheduler
├── scheduler.py             10 APScheduler jobs (reminders, briefings, etc.)
├── config.py                Pydantic Settings (env vars)
├── database.py              AsyncEngine + session factory
│
├── api/                     REST API — тонкий HTTP-слой
│   ├── admin/               10 модулей: dashboard, rooms, tags, events,
│   │                        guests, projects, briefing, messaging, audit, organizers
│   ├── experts/             5 модулей: crud, matching, invites, coverage, escalations
│   └── *.py                 auth, users, events, projects, schedule,
│                            guests, participation, reminders, leads, monitoring
│
├── bot/                     Telegram-бот (ConversationHandler)
│   ├── handlers/            start, qa, followup, business_followup, contact
│   ├── keyboards.py         InlineKeyboard builders
│   └── utils.py             Форматирование, парсинг
│
├── services/                Бизнес-логика (без HTTP, без ORM-запросов)
│   ├── core/                user_service, llm_client, embedding_service, send_retry
│   ├── admin/               22 сервиса: clustering, matching, coverage, schedule,
│   │                        briefing, messaging, notifications, reminders, ...
│   └── guest/               profiling, qa, contact, followup, business_followup
│
├── repos/                   Data Access Layer (async SQLAlchemy queries)
│   ├── event_repo.py        get_current_event, get_approved_clustering
│   ├── user_repo.py         upsert, get_by_telegram_id, roles
│   ├── tag_repo.py          CRUD, get_name_to_id_map
│   ├── expert_repo.py       get_by_id, get_experts, count_by_event
│   ├── project_repo.py      get_by_id, count_by_event, get_with_descriptions
│   ├── room_repo.py         get_by_event, count_projects/experts
│   ├── notification_repo.py CRUD notifications, batches
│   ├── schedule_repo.py     slots, change_logs
│   ├── guest_repo.py        guest profiles, recommendations
│   └── participation_repo.py participation requests
│
├── models/                  SQLAlchemy 2.0 ORM (30 моделей, 24 таблицы)
├── schemas/                 Pydantic request/response (8 файлов)
│
└── worker/                  Celery tasks (LLM, clustering, embeddings)
    ├── celery_app.py        Celery инстанс (RabbitMQ + Redis)
    ├── tasks.py             9 async tasks
    └── utils.py             worker_session(), run_async(), task status
```

## Потоки данных

```
Telegram → bot/handlers → services → repos → PostgreSQL
Browser  → api/         → services → repos → PostgreSQL
Celery   → worker/tasks → services → repos → PostgreSQL
                                    → llm_client     → OpenRouter API
                                    → embedding      → Qdrant
```

## Ключевые принципы

- **Services** не знают о HTTP и Telegram — принимают `session` + данные
- **Repos** — async-функции, только `select`/`insert`/`update`/`delete`
- **`MessageSender` Protocol** вместо прямой зависимости на `telegram.Bot`
- **Worker tasks** используют `async with worker_session()` для управления сессиями
- **API-роуты** — тонкий слой: парсинг запроса → вызов сервиса → формирование ответа

---

## Модули подробно

### `main.py`

App factory. Создаёт FastAPI, настраивает CORS (localhost:5173, localhost:3000, evt-ai.ru), подключает 12 роутеров с префиксом `/api/v1`, health-check на `/health`.

### `lifespan.py`

Управление жизненным циклом:

**Startup:**
1. `Base.metadata.create_all` — создание таблиц (если нет)
2. `organizer_service.seed_from_env` — загрузка организаторов из env
3. Telegram-бот — webhook или polling режим
4. APScheduler — 10 периодических задач

**Shutdown:**
1. Остановка scheduler
2. Остановка bot polling/webhook
3. Graceful shutdown

Все ошибки на startup — non-fatal (логируются, приложение продолжает работу).

### `config.py`

Pydantic Settings с загрузкой из `.env`. Ключевые переменные:

| Переменная | Назначение | Default |
|-----------|-----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://demoday:demoday@localhost:5432/demoday` |
| `BOT_TOKEN` | Telegram Bot API token | — |
| `BOT_MODE` | `polling` или `webhook` | `polling` |
| `SECRET_KEY` | JWT signing key | `dev-secret-key` |
| `WEBHOOK_URL` | Public URL для webhook | — |
| `OPENROUTER_API_KEY` | Один API ключ (backward compat) | — |
| `OPENROUTER_API_KEYS` | Comma-separated ключи (ротация) | — |
| `OPENROUTER_MODEL` | Модель LLM | `openai/gpt-4.1` |
| `ORGANIZER_TELEGRAM_IDS` | Comma-separated Telegram ID организаторов | — |
| `ORGANIZER_TELEGRAM_USERNAMES` | Comma-separated usernames | — |
| `TEAM_CHAT_ID` | Chat ID для уведомлений команде | — |
| `RABBITMQ_URL` | RabbitMQ connection | `amqp://demoday:demoday@localhost:5672//` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `QDRANT_URL` | Qdrant vector DB | `http://localhost:6333` |
| `EMBEDDING_MODEL` | Модель эмбеддингов | `google/gemini-embedding-001` |
| `EMBEDDING_DIMENSIONS` | Размерность вектора | `768` |

Properties: `api_keys` (список с ротацией), `organizer_ids` (set), `organizer_usernames` (set), `is_organizer(user_id, username)`.

### `database.py`

SQLAlchemy async engine + session factory. `get_session()` — async generator для FastAPI Depends.

---

## API

### Публичные роуты

| Модуль | Prefix | Назначение |
|--------|--------|-----------|
| `auth.py` | `/auth` | Login (Telegram widget), dev-login |
| `users.py` | `/users` | GET /me, GET /{id} |
| `events.py` | `/events` | GET /current |
| `projects.py` | `/projects` | Upload, list, clustering, room management |
| `schedule.py` | `/schedule` | Generate, get, approve, notify |
| `guests.py` | `/guests` | Profile create/get, tags |
| `participation.py` | `/participation` | Requests, approve/reject |
| `leads.py` | `/leads` | Capture leads |
| `monitoring.py` | `/monitoring` | Stats, health |

### Admin API (`/api/v1/admin/`)

10 подроутеров, собранных в `api/admin/__init__.py`:

| Модуль | Функционал |
|--------|-----------|
| `dashboard.py` | Метрики, покрытие, статистика |
| `rooms.py` | CRUD комнат, тематика |
| `tags.py` | CRUD тегов, нормализация, LLM-подсказки |
| `events.py` | Управление текущим событием |
| `guests.py` | Список гостей, профили, upload |
| `projects.py` | Список проектов, фильтрация |
| `briefing.py` | Генерация и отправка брифингов экспертам |
| `messaging.py` | Массовая рассылка через Telegram |
| `audit.py` | Лог действий администраторов |
| `organizers.py` | CRUD организаторов |

### Experts API (`/api/v1/experts/`)

5 подроутеров в `api/experts/__init__.py`:

| Модуль | Функционал |
|--------|-----------|
| `crud.py` | Upload, create, update, list, get |
| `matching.py` | Запуск мэтчинга, текущие назначения, перемещение |
| `invites.py` | Превью, отправка приглашений |
| `coverage.py` | Покрытие залов, пробелы, детали |
| `escalations.py` | Список эскалаций, разрешение |

### Аутентификация

JWT (HS256). Два режима:
- **Production:** Telegram Login Widget → verify HMAC → issue JWT
- **Dev:** `POST /auth/dev-login` с user_id (только при `SECRET_KEY=dev-secret-key`)

Middleware: `get_current_user` (из `deps.py`) декодирует JWT из `Authorization: Bearer <token>`. `check_organizer` — проверка роли ORGANIZER.

---

## Services

### Core (`services/core/`)

| Сервис | Файл | Назначение |
|--------|------|-----------|
| **UserService** | `user_service.py` | Upsert пользователей, роли, текущее событие, гостевые профили |
| **LLMClient** | `llm_client.py` | OpenRouter API с ротацией ключей, structured output, retry |
| **EmbeddingService** | `embedding_service.py` | Google Gemini эмбеддинги → Qdrant (cosine search) |
| **SendRetry** | `send_retry.py` | `MessageSender` Protocol + `send_with_retry()` с exponential backoff |

`MessageSender` Protocol — абстракция для отправки сообщений, позволяет сервисам не зависеть от `telegram.Bot`:

```python
@runtime_checkable
class MessageSender(Protocol):
    async def send_message(self, chat_id: int | str, text: str, **kwargs) -> None: ...
```

### Admin (`services/admin/`)

22 сервиса. Основные:

| Сервис | Строк | Назначение |
|--------|-------|-----------|
| `notification_service.py` | ~1227 | Eve-of-DD, pre-slot, timing-shift уведомления, батчинг |
| ~~`reminder_service.py`~~ | — | REMOVED (dead code, functionality in notification_service) |
| `invite_service.py` | ~641 | Приглашение экспертов, эскалация, переназначение |
| `schedule_service.py` | ~518 | Генерация расписания из кластеризации |
| `dashboard_service.py` | ~515 | Метрики события, статистика |
| `participation_service.py` | ~488 | Заявки на участие, напоминания, сводки |
| `matching_service.py` | ~435 | Мэтчинг экспертов ↔ залам по тегам |
| `coverage_service.py` | ~386 | Расчёт покрытия (эксперт/зал) |
| `clustering_service.py` | ~363 | LLM-кластеризация проектов по залам |
| `project_service.py` | ~327 | Загрузка проектов (CSV/XLSX/JSON), парсинг |
| `briefing_service.py` | ~288 | Генерация LLM-брифов для экспертов |
| `expert_service.py` | ~206 | Загрузка экспертов, оценки |
| `messaging_service.py` | ~173 | Рассылка сообщений через Telegram |
| `tag_service.py` | ~120 | CRUD тегов, нормализация |
| `background_jobs.py` | ~126 | In-memory tracking длительных операций |
| `organizer_service.py` | ~95 | Seed организаторов из ENV |
| `dedup_service.py` | ~54 | Дедупликация проектов |
| `audit_service.py` | ~53 | Логирование действий |
| `guest_admin_service.py` | ~273 | Админ-CRUD гостевых профилей |
| `github_service.py` | ~117 | Парсинг GitHub URL (tech stack, README) |

### Guest (`services/guest/`)

5 сервисов для гостевого пути:

| Сервис | Строк | Назначение |
|--------|-------|-----------|
| `profiling_service.py` | ~763 | LLM-диалог профилирования, извлечение интересов, теги |
| `qa_service.py` | ~383 | Q&A помощник: вопросы под профиль + матрица сравнения |
| `business_followup_service.py` | ~298 | Бизнес follow-up: письма LOI, шаблоны |
| `followup_service.py` | ~238 | Follow-up пакет: резюме, контакты, next steps |
| `contact_service.py` | ~176 | Запросы контактов авторов проектов |

---

## Models

30 моделей, 24 таблицы в PostgreSQL. Все наследуют `Base` (declarative_base).

### Пользователи и роли

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `User` | `users` | id, telegram_user_id, full_name, username, guest_subtype |
| `Role` | `roles` | id, code (enum: ORGANIZER, EXPERT, STUDENT, GUEST), name |
| `UserRole` | `user_roles` | user_id → users, role_id → roles, event_id → events |
| `Organizer` | `organizers` | id, user_id → users |

`GuestSubtype` enum: STUDENT, APPLICANT, OTHER, INVESTOR, BUSINESS_PARTNER, MENTOR, HR, JURY.

### События и проекты

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `Event` | `events` | id, name, start_date, end_date, description |
| `Project` | `projects` | id, title, description, author, telegram_contact, github_url, tech_stack, event_id |
| `Tag` | `tags` | id, name, description |
| `ProjectTag` | `project_tags` | project_id, tag_id |
| `Room` | `rooms` | id, name, theme, event_id |
| `RoomProject` | `room_projects` | room_id, project_id, display_order |
| `ClusteringRun` | `clustering_runs` | id, status (PREVIEW/CONFIRMED/COMPLETED), event_id |

### Профилирование гостей

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `GuestProfile` | `guest_profiles` | user_id, selected_tags[], extracted_tags[], keywords[], raw_text |
| `BusinessProfile` | `business_profiles` | user_id, objective (enum), requirements |
| `Recommendation` | `recommendations` | guest_id, project_id, match_score |
| `ProjectRecommendation` | `project_recommendations` | user_id, project_id, score, reasoning |

### Эксперты

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `Expert` | `experts` | id, name, email, telegram_id, organization, score |
| `ExpertTag` | `expert_tags` | expert_id, tag_id |
| `ExpertRoomAssignment` | `expert_room_assignments` | expert_id, room_id, event_id, status |
| `ExpertBriefing` | `expert_briefings` | expert_id, summary, status (PENDING/SENT/OPENED) |
| `Escalation` | `escalations` | assignment_id, escalation_level |

### Расписание и уведомления

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `ScheduleSlot` | `schedule_slots` | project_id, room_id, start_time, end_time, status |
| `ScheduleChangeLog` | `schedule_change_logs` | slot_id, change_type (CREATED/MOVED/CANCELLED) |
| `Notification` | `notifications` | user_id, type (EVE_OF_DD/PRE_SLOT/TIMING_SHIFT), status |
| `ReminderBatch` | `reminder_batches` | DEPRECATED — not in active use, kept for migration history |
| `ReminderNotification` | `reminder_notifications` | DEPRECATED — not in active use, kept for migration history |

### Участие и follow-up

| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| `ParticipationRequest` | `participation_requests` | user_id, project_id, status (PENDING/APPROVED) |
| `QASuggestion` | `qa_suggestions` | project_id, question_type, suggested_questions[] |
| `ContactRequest` | `contact_requests` | user_id, project_id, status |
| `FollowupPackage` | `followup_packages` | user_id, event_id |
| `BusinessFollowup` | `business_followups` | contact_request_id, letter_template |
| `AdminAuditLog` | `admin_audit_logs` | admin_id, action, entity_type, details |

---

## Telegram Bot

python-telegram-bot 21.x, ConversationHandler (state machine).

### Handlers

| Handler | Файл | Назначение |
|---------|------|-----------|
| Start/Main | `handlers/start.py` | Главный диалог: онбординг → профиль → меню → рекомендации |
| Q&A | `handlers/qa.py` | Q&A помощник: вопросы + матрица сравнения |
| Follow-up | `handlers/followup.py` | Follow-up пакет |
| Business | `handlers/business_followup.py` | Бизнес follow-up, письма LOI |
| Contact | `handlers/contact.py` | Запросы контактов |

### Пользовательский путь

```
/start
  → Выбор субтипа (студент, абитуриент, инвестор, HR, ментор, жюри, другое)
  → Профилирование (LLM-диалог или выбор тегов)
  → Бизнес-профиль (для non-студентов)
  → Главное меню
    ├── Рекомендации → топ проектов с рейтингом
    ├── Q&A помощник → вопросы по проектам
    ├── Follow-up → резюме, контакты, next steps
    └── Поиск → поиск по критериям
```

---

## Celery Worker

### Конфигурация

- **Broker:** RabbitMQ (`amqp://demoday:demoday@localhost:5672//`)
- **Backend:** Redis (`redis://localhost:6379/0`)
- **Workers:** 2 (default + heavy)
- **Concurrency:** prefork (default)

### DB-сессии в worker

Singleton engine инициализируется через Celery signal `worker_process_init`. Задачи используют `worker_session()`:

```python
@celery_app.task
def my_task():
    async def _run():
        async with worker_session() as session:
            # ... работа с БД
    run_async(_run())
```

### Tasks

| Task | Назначение |
|------|-----------|
| `chat_for_profile_task` | LLM-диалог профилирования |
| `extract_interests_from_text_task` | Извлечение интересов из текста (LLM) |
| `generate_recommendations_task` | Генерация рекомендаций (embedding + cosine search) |
| `send_qa_helper_task` | Q&A вопросы (LLM) |
| `send_briefing_task` | Брифинг экспертам (LLM) |
| `clustering_task` | Кластеризация проектов по залам (LLM) |
| `generate_followup_task` | Follow-up пакет (LLM) |
| `generate_business_followup_task` | Бизнес follow-up письма (LLM) |
| `process_contact_request_task` | Обработка запроса контактов |

### Утилиты (`worker/utils.py`)

| Функция | Назначение |
|---------|-----------|
| `init_db_engine()` | Создание DB engine (pool_size=3, max_overflow=2) |
| `shutdown_db_engine()` | Dispose engine |
| `run_async(coro)` | Запуск async в sync Celery task |
| `worker_session()` | Async context manager для DB session |
| `wait_for_task(task_id, timeout)` | Async ожидание завершения task |
| `get_task_status(task_id)` | Статус task (pending/running/completed/failed) |
| `revoke_task(task_id)` | Отмена task |

---

## APScheduler

10 периодических задач, таймзона MSK (Europe/Moscow):

| Job ID | Trigger | Частота | Функция |
|--------|---------|---------|---------|
| `expert_reminders` | Interval | 12ч | Напоминания экспертам об ответе на приглашение |
| `escalations` | Interval | 12ч | Эскалация неответивших экспертов |
| `participation_reminders` | Interval | 1ч | Напоминания по заявкам на участие |
| `participation_escalations` | Interval | 1ч | Эскалация по заявкам → организаторам |
| `eve_reminder_preview` | Cron | 17:00 MSK | Превью напоминаний организаторам (за день до DD) |
| `eve_reminder_send` | Cron | 18:00 MSK | Отправка eve-of-DD напоминаний |
| `pre_slot_reminders` | Interval | 5мин | Напоминания за ~1ч до слота |
| `batch_processor` | Interval | 60сек | Обработка pending batches (timing shift) |
| `expert_briefing` | Cron | 18:00 MSK | Отправка брифингов экспертам (за день до DD) |

Все jobs принимают `bot` и `session_factory` как аргументы. Каждый job оборачивает логику в try/except с логированием.

---

## Миграции

Alembic, 27 версий. Ключевые:

| Версия | Описание |
|--------|----------|
| 001 | Initial: users, events, projects, tags, rooms |
| 002 | Clustering: clustering_runs, room_projects |
| 003/003a/003b | Business profiles, expert assignments, guest profiling |
| 004-006 | Reminders: schedule_slots, notifications, reminder_notifications |
| 008 | Expert briefings, github_url, tech_stack |
| 009-010 | QA suggestions, contact requests |
| 014-015 | Followup packages, business followups |
| 020/024 | GuestSubtype extend (INVESTOR, BUSINESS_PARTNER, MENTOR, HR, JURY) |
| 021-022 | Audit log, organizers |

Запуск: `alembic upgrade head`.

---

## Тесты

pytest + pytest-asyncio, `asyncio_mode = "auto"`.

| Файл | Покрытие |
|------|----------|
| `test_admin_api.py` | API: projects upload, clustering, schedule |
| `test_auth.py` | Telegram auth, JWT, dev-login |
| `test_clustering.py` | LLM-кластеризация (мок) |
| `test_send_retry.py` | Retry с exponential backoff |
| `test_audit_service.py` | Логирование действий |
| `test_organizer_service.py` | Seed организаторов |
| `test_dedup_service.py` | Дедупликация проектов |
| `test_dependency_imports.py` | Проверка импортов |
| `test_alembic_heads.py` | Единственный head в миграциях |
| `test_alembic_upgrade.py` | Миграции применяются без ошибок |
| `test_smoke_imports.py` | Smoke-тест импортов |
| `test_handlers/` | Telegram handlers: onboarding, Q&A |
| `e2e/test_agent.py` | E2E с реальным Telegram (не в CI) |

Запуск:
```bash
cd backend
.venv/bin/python -m pytest tests/ --ignore=tests/e2e -v
```

---

## Локальная разработка

### Переменные окружения

```bash
cp .env.example .env
# Заполнить: BOT_TOKEN, OPENROUTER_API_KEY (минимум)
```

### Docker Compose

```bash
docker compose up -d   # PostgreSQL, RabbitMQ, Redis, Qdrant
```

### Запуск backend

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Запуск Celery worker

```bash
cd backend
.venv/bin/celery -A app.worker.celery_app worker --loglevel=info
```

### Линтер

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/ruff check . --fix  # автофикс
```

---

## Production

- **Сервер:** Yandex Cloud VM (2 vCPU, 4GB RAM, 20GB SSD)
- **Домен:** evt-ai.ru
- **Деплой:** GitHub Actions CD → SSH → git pull → `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`
- **Мониторинг:** RabbitMQ (`/rabbitmq/`), Flower (`/flower/`), API Docs (`/docs`)
