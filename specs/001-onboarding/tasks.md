# Tasks: Онбординг и выбор роли

**Input**: Design documents from `specs/001-onboarding/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/openapi.yaml

**Tests**: Не запрошены в спецификации. Тестовые задачи не включены.

**Organization**: Задачи сгруппированы по user stories для независимой реализации и тестирования.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Можно запускать параллельно (разные файлы, нет зависимостей)
- **[Story]**: К какому user story относится (US1, US2, US3)
- Пути файлов указаны от корня репозитория

---

## Phase 1: Setup (Инициализация проекта)

**Purpose**: Создать структуру проекта, зависимости, Docker-окружение

- [ ] T001 Создать структуру директорий проекта: `backend/app/{models,schemas,api,services,bot/handlers}/`, `backend/tests/`, `backend/alembic/versions/`
- [ ] T002 Создать `backend/pyproject.toml` с зависимостями: fastapi, uvicorn, python-telegram-bot==21.*, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-jose[cryptography]; dev: pytest, pytest-asyncio, httpx
- [ ] T003 [P] Создать `docker-compose.yml` в корне: PostgreSQL 16 (порт 5432, volume для данных, credentials из .env)
- [ ] T004 [P] Создать `backend/.env.example` с переменными: DATABASE_URL, BOT_TOKEN, BOT_MODE, ORGANIZER_TELEGRAM_IDS, SECRET_KEY
- [ ] T005 [P] Создать `backend/Dockerfile`: python:3.12-slim, pip install, CMD uvicorn

---

## Phase 2: Foundational (Блокирующие предпосылки)

**Purpose**: Инфраструктура БД, модели, сервис пользователей — БЛОКИРУЕТ все user stories

**CRITICAL**: Работа над user stories невозможна до завершения этой фазы

- [ ] T006 Создать `backend/app/config.py`: Pydantic BaseSettings с полями DATABASE_URL, BOT_TOKEN, BOT_MODE (polling/webhook), ORGANIZER_TELEGRAM_IDS (comma-separated → set[str]), SECRET_KEY
- [ ] T007 Создать `backend/app/database.py`: async SQLAlchemy engine (create_async_engine), async sessionmaker, get_session dependency
- [ ] T008 Создать `backend/app/models/base.py`: DeclarativeBase с общими полями id (UUID, server_default), created_at, updated_at
- [ ] T009 [P] Создать `backend/app/models/role.py`: Role(Base) — id, code (unique), name. Enum RoleCode: organizer/student/expert/guest/business
- [ ] T010 [P] Создать `backend/app/models/event.py`: Event(Base) — id, name, start_date, end_date
- [ ] T011 Создать `backend/app/models/user.py`: User(Base) — id, telegram_user_id (unique), full_name, username (nullable), guest_subtype (enum: applicant/ai_practitioner/other, nullable)
- [ ] T012 Создать `backend/app/models/user_role.py`: UserRole(Base) — id, user_id (FK), role_id (FK), event_id (FK), UniqueConstraint(user_id, event_id)
- [ ] T013 Создать `backend/app/models/__init__.py`: реэкспорт всех моделей
- [ ] T014 Инициализировать Alembic: `backend/alembic.ini` + `backend/alembic/env.py` (async, импорт всех моделей из app.models)
- [ ] T015 Создать первую миграцию Alembic в `backend/alembic/versions/001_initial_schema.py`: создание таблиц users, roles, events, user_roles + seed-данные (5 ролей, 1 событие "Demo Day 2026-02-06")
- [ ] T016 Создать `backend/app/schemas/user.py`: Pydantic-схемы TelegramAuthRequest, SetRoleRequest, SetGuestSubtypeRequest, UserProfile, RoleInfo, AuthResponse, ErrorResponse (по OpenAPI-контракту)
- [ ] T017 Создать `backend/app/services/user_service.py`: UserService с методами: upsert_user(telegram_user_id, full_name, username) → User (INSERT ON CONFLICT DO UPDATE), get_user_by_telegram_id(telegram_user_id) → User|None, set_role(user_id, event_id, role_code, guest_subtype?) → UserRole (INSERT ON CONFLICT DO UPDATE + сброс guest_subtype при смене с guest), get_user_role(user_id, event_id) → UserRole|None
- [ ] T018 Создать `backend/app/main.py`: FastAPI app с lifespan (инициализация БД, запуск бота), подключение API-роутеров, webhook endpoint для Telegram (если BOT_MODE=webhook), polling fallback (если BOT_MODE=polling)

**Checkpoint**: Фундамент готов — можно начинать user stories

---

## Phase 3: User Story 1 — Первый вход и выбор роли (Priority: P1) MVP

**Goal**: Новый пользователь отправляет /start, выбирает роль из 5, видит меню роли. Организатор защищён whitelist.

**Independent Test**: Отправить /start → увидеть 5 кнопок → нажать роль → увидеть меню

- [ ] T019 [US1] Создать `backend/app/bot/keyboards.py`: функция role_selection_keyboard() → InlineKeyboardMarkup с 5 кнопками (callback_data: "role:organizer", "role:student", "role:expert", "role:guest", "role:business"); функция role_menu_keyboard(role_code) → InlineKeyboardMarkup с placeholder-кнопками для каждой роли
- [ ] T020 [US1] Создать `backend/app/bot/handlers/start.py`: ConversationHandler с entry_point CommandHandler("start"); состояние CHOOSING_ROLE; обработчик нового пользователя: upsert_user → показать приветствие + role_selection_keyboard; fallback для нетекстовых сообщений (FR-009)
- [ ] T021 [US1] Создать `backend/app/bot/handlers/role.py`: CallbackQueryHandler для callback_data "role:*"; проверка whitelist для organizer (FR-003, config.organizer_telegram_ids); при успехе: set_role + показать role_menu_keyboard; при отказе организатора: сообщение "Роль организатора доступна только по приглашению" + повторный показ role_selection_keyboard; защита от double-tap (FR-010): answer_callback_query с сообщением "Роль уже выбрана" если роль не изменилась
- [ ] T022 [US1] Создать `backend/app/bot/app.py`: функция create_bot_application(config) → Application; регистрация ConversationHandler из start.py; настройка webhook/polling по BOT_MODE
- [ ] T023 [US1] Создать `backend/app/api/auth.py`: FastAPI router; POST /auth/login (upsert user, вернуть JWT + UserProfile); GET /auth/me (текущий пользователь + роль в текущем событии)
- [ ] T024 [US1] Интеграция: подключить bot.app и api.auth в main.py, проверить end-to-end: docker-compose up → /start → выбор роли → меню

**Checkpoint**: US1 полностью функциональна и тестируема независимо

---

## Phase 4: User Story 2 — Выбор подтипа гостя (Priority: P2)

**Goal**: После выбора "Гость" — второй экран с подтипами. Подтип сохраняется для аналитики.

**Independent Test**: Выбрать роль "Гость" → увидеть 3 кнопки подтипов → нажать → меню гостя

- [ ] T025 [US2] Добавить в `backend/app/bot/keyboards.py`: функция guest_subtype_keyboard() → InlineKeyboardMarkup с 3 кнопками (callback_data: "subtype:applicant", "subtype:ai_practitioner", "subtype:other")
- [ ] T026 [US2] Добавить в `backend/app/bot/handlers/start.py`: состояние CHOOSING_SUBTYPE в ConversationHandler; при выборе role:guest → переход в CHOOSING_SUBTYPE → показать guest_subtype_keyboard; для остальных ролей — сразу END
- [ ] T027 [US2] Добавить в `backend/app/bot/handlers/role.py`: CallbackQueryHandler для callback_data "subtype:*"; сохранить guest_subtype через user_service.set_role(..., guest_subtype=value); показать role_menu_keyboard("guest")
- [ ] T028 [US2] Добавить в `backend/app/api/auth.py`: PUT /users/me/guest-subtype (SetGuestSubtypeRequest → UserProfile; 403 если роль не guest)
- [ ] T029 [US2] Проверить: для роли "Бизнес-партнёр" экран подтипов НЕ показывается (acceptance scenario 3)

**Checkpoint**: US1 и US2 работают независимо

---

## Phase 5: User Story 3 — Возврат и смена роли (Priority: P3)

**Goal**: Повторный /start или /role → продолжить или сменить роль. При смене guest → другая роль — сброс подтипа.

**Independent Test**: /start как существующий пользователь → "Продолжить / Сменить" → выбор новой роли

- [ ] T030 [US3] Добавить в `backend/app/bot/keyboards.py`: функция continue_or_change_keyboard() → InlineKeyboardMarkup: "Продолжить" (callback_data: "action:continue"), "Сменить роль" (callback_data: "action:change")
- [ ] T031 [US3] Обновить `backend/app/bot/handlers/start.py`: при повторном /start (user существует + есть роль) → показать "Вы зарегистрированы как {role}. Продолжить?" + continue_or_change_keyboard; callback "action:continue" → показать role_menu_keyboard текущей роли; callback "action:change" → показать role_selection_keyboard (переход в CHOOSING_ROLE)
- [ ] T032 [US3] Создать обработчик команды /role в `backend/app/bot/handlers/role.py`: CommandHandler("role"); логика аналогична повторному /start (текущая роль + continue_or_change); зарегистрировать в bot/app.py
- [ ] T033 [US3] Обновить `backend/app/services/user_service.py`: при set_role — если предыдущая роль была guest и новая роль не guest, сбросить users.guest_subtype = NULL
- [ ] T034 [US3] Проверить: смена "Гость (AI-практик)" → "Студент" → подтип сброшен; /role показывает "Студент"

**Checkpoint**: Все user stories функциональны и независимо тестируемы

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, логирование, финальная проверка

- [ ] T035 [P] Обработка edge cases в `backend/app/bot/handlers/`: нетекстовые сообщения до выбора роли (стикер, фото → повторить предложение); организатор удалён из whitelist → при /start предлагает сменить роль
- [ ] T036 [P] Добавить structured logging в `backend/app/bot/handlers/start.py` и `role.py`: логировать выбор роли, смену роли, попытку доступа к роли организатора
- [ ] T037 Пройти `specs/001-onboarding/quickstart.md`: все 4 ручных теста должны работать

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Нет зависимостей — начинать сразу
- **Foundational (Phase 2)**: Зависит от Setup — БЛОКИРУЕТ все user stories
- **US1 (Phase 3)**: Зависит от Foundational — первый MVP-инкремент
- **US2 (Phase 4)**: Зависит от Foundational. Расширяет файлы из US1, но может разрабатываться параллельно при аккуратном мерже
- **US3 (Phase 5)**: Зависит от Foundational. Расширяет файлы из US1/US2
- **Polish (Phase 6)**: Зависит от всех user stories

### Within Each User Story

- Keyboards → Handlers → Integration
- Service layer уже создан в Foundational (T017)

### Parallel Opportunities

```bash
# Phase 1: все [P] задачи параллельно
T003, T004, T005

# Phase 2: модели параллельно
T009, T010  # Role и Event не зависят друг от друга

# Phase 6: polish параллельно
T035, T036
```

---

## Implementation Strategy

### MVP First (только User Story 1)

1. Phase 1: Setup (T001-T005)
2. Phase 2: Foundational (T006-T018)
3. Phase 3: User Story 1 (T019-T024)
4. **STOP и VALIDATE**: /start → роль → меню работает
5. Deploy / demo-ready

### Incremental Delivery

1. Setup + Foundational → Фундамент готов
2. US1 → Deploy (MVP!)
3. US2 → Подтипы гостей → Deploy
4. US3 → Смена роли → Deploy
5. Polish → Финальная версия

---

## Notes

- Тесты не включены (не запрошены в спецификации)
- Все модели создаются в Foundational, т.к. используются всеми user stories
- UserService создаётся в Foundational с полным набором методов — это CRUD без бизнес-логики user stories
- Меню ролей — заглушки (placeholder-кнопки) до реализации EPIC-002+
- BOT_MODE=polling для локальной разработки, webhook для production
