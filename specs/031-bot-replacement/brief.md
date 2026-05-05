# Бриф: Замена бота-агента в demoday-core на bonus-track-llm

> **Статус:** Draft v1.0
> **Дата:** 2026-05-03
> **Автор:** Кларифайер (бизнес-аналитик)
> **Тип:** Migration / Replacement

---

## Что нужно сделать?

**Описание задачи:**
Заменить существующего Telegram-бота гостя в `demoday-core` (python-telegram-bot, встроенный в FastAPI lifespan) на агента из проекта `bonus-track-llm` (aiogram 3.x + PydanticAI + pgvector + 8 инструментов агента + GitHub-анализ + парсинг артефактов + PDF-экспорт + llm-agent-platform).

Админка `demoday-core` сохраняется целиком и продолжает работать с той же БД.

**Job Story:**
Когда гость Demo Day открывает Telegram-бота, я хочу, чтобы он получил умного AI-куратора с диалоговым профилированием, vector-рекомендациями, сравнением проектов, GitHub-анализом и PDF-программой, при этом организатор продолжал управлять событием через привычную админку без потери функционала.

---

## Полезное действие (Зачем?)

Не обсуждается -- задача поставлена как «просто сделать качественно». Мотивация и сроки за рамками брифа.

---

## Жёсткие ограничения (Constraints)

| Параметр | Значение |
|---|---|
| **Telegram bot token** | Тот же самый, что используется сейчас. Тот же `@username` |
| **База данных** | **Единая** PostgreSQL. Real-time согласованность между админкой и ботом. Изменение в админке мгновенно видно боту |
| **Админка** | Сохраняется на 100% (~20 React-страниц, все API в `/api/v1/admin/*`) |
| **Scheduler** | APScheduler с напоминаниями (eve-of-DD, pre-slot, escalations, expert briefing) сохраняется и продолжает слать сообщения через тот же bot token |
| **История диалогов гостей** | Не мигрируется (синтетика, можно потерять) |
| **Качество** | Качество > скорости. Дедлайна нет. Делаем «хорошо» |
| **LLM-стек** | Bonus как есть: `llm-agent-platform` (Prometheus / Grafana / Langfuse / circuit breaker / guardrails) + DeepSeek V3.2 + Gemini embeddings 3072d |
| **Бот-функционал** | Только то, что покрывает bonus-track-llm. Все 8 tools обязательны |

---

## Что нужно сделать боту (функционал из bonus-track-llm)

### 8 инструментов агента (все обязательны)

| Tool | Описание |
|---|---|
| `show_project` | Карточка проекта: описание, стек, метрики из артефактов (PPTX/PDF/README), автор |
| `show_profile` | Текущий профиль гостя: теги, цели, summary, бизнес-поля |
| `compare_projects` | LLM-матрица сравнения 2-5 проектов |
| `generate_questions` | 3-5 вопросов для Q&A автору, персонализированы под роль |
| `filter_projects` | Фильтр рекомендаций по тегу/технологии (case-insensitive) |
| `get_summary` | Follow-up пакет (контакты + шаблон) для гостя или бизнес-пайплайн для бизнеса |
| `update_status` | Бизнес-пайплайн: interested / contacted / meeting_scheduled / rejected / in_progress |
| `github_drilldown` | Live-анализ GitHub-репозитория через `gh` CLI (метрики, файлы, структура, коммиты, контрибьюторы) |

### Сопутствующие сервисы

- Парсинг артефактов: PPTX (`python-pptx`), PDF (`pymupdf`), GitHub README → LLM structured extraction
- PDF-экспорт программы (`fpdf2` + DejaVu)
- Embedding (Gemini 3072d) → pgvector cosine search → schedule-aware rerank
- Поддержка (`support_log` + `correlation_id`, ответы организатора через support_group_router)
- Деградация: LLM недоступна → tag overlap scoring, timeout → fallback
- Базовый эксперт-флоу: оценка проектов 1-5 по критериям мероприятия

### Сценарии бота

- Профилирование гостя (LLM 2-3 хода + force extraction)
- Рекомендации проектов (vector search)
- Диалог с агентом (8 tools)
- Поддержка (вопрос организатору, ответ через group router)
- Бизнес-пайплайн (для роли business)
- Эксперт-флоу (минимальный, как в bonus)

---

## Что админка продолжает делать (сохранение)

| Страница админки | Статус | Комментарий |
|---|---|---|
| `Dashboard` | сохраняется | Базовые сущности, не требует изменений |
| `ProjectsList` / `ProjectDetail` | сохраняется | Источник правды по проектам |
| `Schedule` / `RoomDetail` | сохраняется | Источник правды по расписанию |
| `ExpertList` / `ExpertMatching` | сохраняется | Расширенный эксперт-флоу остаётся в админке. Бот покрывает только базовый из bonus |
| `GuestList` | сохраняется | |
| `Tags` | сохраняется | Источник правды по тегам |
| `Settings` | сохраняется | Включая Settings для LLM-ключей -- остаётся в UI, но ботом не используется (бот ходит через `llm-agent-platform`) |
| `SupportChat` | сохраняется + поддерживается ботом | Бот через `support_log` пишет вопросы, организатор отвечает через `support_group_router` или UI |
| `Messaging` | сохраняется + поддерживается ботом | Ручные рассылки от организаторов идут через нового бота |
| `DataImport` | сохраняется | |
| `Event` / `Login` / `Landing` | сохраняется | |
| `Participants` (participation requests) | **Open Question** | Сценарий не входит в bonus. Default: оставить страницу как read-only/legacy для просмотра старых заявок. Подтвердить решение |

**Принцип:** админка остаётся целиком как UI. Если страница работает с сущностью, которой бот больше не управляет -- страница остаётся (read-only при необходимости). Не переписываем фронт.

---

## Что нужно учесть?

### Расхождение моделей данных

| Параметр | demoday-core | bonus-track-llm |
|---|---|---|
| Количество таблиц | ~38 моделей | 13 таблиц |
| Управление схемой | Alembic (38 миграций) | `schema.sql` |
| Vector search | Qdrant 768d, частично tags | pgvector 3072d (Gemini) |
| Роли пользователей | enum `guest_subtype` (student, applicant, investor, business_partner, mentor, hr, jury) | enum `role_code` (guest, business, expert) |
| Структура `Project` | поля под admin-флоу, контактные реквесты, briefing | минимум полей + `embedding` + `parsed_content` |

**Требуется маппинг и расширение схемы:**
- Добавить расширение `pgvector` в demoday-БД
- Добавить колонку `embedding vector(3072)` в `projects`
- Добавить колонку `parsed_content jsonb` в `projects`
- Добавить таблицы из bonus, которых нет в demoday: `recommendations`, `chat_messages`, `business_followups`, `support_log` (или смапить на существующие)
- Смапить `users.role_code` ↔ `users.guest_subtype`

### LLM-инфраструктура

- Существующий `llm_client` от demoday с ротацией ключей из БД (`llm_api_keys`) ботом **больше не используется**
- Бот ходит через `llm-agent-platform` (DeepSeek V3.2 + Gemini embeddings)
- Settings-страница LLM-ключей остаётся в UI (legacy)

### Telegram bot token shared between bot service and scheduler

- Scheduler в `backend/app/scheduler.py` шлёт сообщения через Bot API
- Messaging-страница админки шлёт ручные рассылки
- Новый бот (отдельный процесс) обрабатывает входящие
- **Open Question архитектору:** как именно делить bot session между процессами (общий HTTP API нового бота / админка использует тот же token напрямую через свой aiogram-клиент только для send / иное)

### Бот в текущем процессе FastAPI

- Сейчас бот запускается внутри `backend/app/lifespan.py` (`bot_app = create_bot_app()` → `await bot_app.start()`)
- Bonus написан как standalone-сервис (без FastAPI; aiogram + aiohttp `/health`)
- Нужно решение архитектора: впихнуть aiogram внутрь FastAPI lifespan ИЛИ вынести в отдельный контейнер docker-compose

---

## Критерии приёмки

- [ ] Гость проходит онбординг, получает программу, может задать любой вопрос агенту
- [ ] Агент использует все 8 tools (показать карточку, сравнить, сгенерить вопросы, GitHub drilldown, фильтр, summary, update_status, show_profile)
- [ ] Парсинг артефактов работает: PPTX/PDF/GitHub README → структурированный JSON в `parsed_content`
- [ ] PDF-экспорт программы доступен пользователю
- [ ] Vector-рекомендации (pgvector cosine + schedule-aware rerank) выдают релевантные проекты
- [ ] Бот деградирует gracefully: LLM-сбой → tag overlap fallback, timeout → fallback-ответ
- [ ] Админка работает без регрессий: все ~20 страниц функциональны
- [ ] Scheduler шлёт напоминания через того же бота (eve-of-DD, pre-slot, escalations, expert briefing)
- [ ] Messaging-страница админки шлёт ручные рассылки через нового бота
- [ ] SupportChat: гость пишет в бота → организатор видит в `SupportChat` UI и/или в Telegram-группе → ответ доходит до гостя
- [ ] Изменение проекта/расписания/тегов в админке мгновенно видно боту (единая БД)
- [ ] Никаких потерь данных в БД админки
- [ ] LLM-стек: `llm-agent-platform` развёрнут, метрики Prometheus / Grafana / Langfuse доступны
- [ ] Конкретные пороги (latency, coverage, downtime) -- не задаются, делаем «хорошо»

---

## Out of Scope

- Сценарии demoday-бота, **не покрытые** bonus:
  - Контакт-реквесты гость → автор проекта (`contact_request`)
  - Расширенный participation-флоу (`participation_requests`, заявки на участие проектов)
  - Расширенный expert-флоу с briefing/room assignment через бота (остаётся только админская часть)
  - QA suggestions через бота (модель `qa_suggestion`) -- заменяется bonus-инструментом `generate_questions`
- Миграция истории диалогов гостей (синтетика)
- Изменение Telegram bot token / username
- Переписывание frontend admin под новую схему
- Удаление legacy-моделей и таблиц из БД (оставляем как есть)
- Сроки, дедлайны, привязка к мероприятию
- Бюджет

---

## Open Questions для архитектора

1. **Архитектура запуска бота:** один процесс с FastAPI (как сейчас) или отдельный контейнер в docker-compose? Bonus написан под standalone, demoday -- под встроенный
2. **Shared bot token:** как админка и scheduler шлют сообщения через того же бота, который сейчас живёт в отдельном процессе? Варианты: общий HTTP API нового бота / прямой доступ к token из админки / иное
3. **Миграция схемы БД:** одной большой миграцией или поэтапно? Оставляем legacy-таблицы demoday или вычищаем?
4. **Маппинг ролей:** как смапить `users.guest_subtype` (8 вариантов) на `users.role_code` (3 варианта)? Хранить оба поля или унифицировать?
5. **Participants-страница:** оставляем как read-only legacy или удаляем?
6. **`llm-agent-platform`:** разворачивать вместе с ботом (Prometheus, Grafana, Langfuse, сам proxy) или достаточно standalone OpenRouter? «Bonus как есть» можно интерпретировать обоими способами
7. **Что делать с моделями demoday, которые больше не используются ботом** (`contact_request`, `participation_request`, `qa_suggestion`, `expert_briefing`, `followup_package`)? Оставляем в коде backend для совместимости с админкой?

---

## Оценка рисков

### Технические риски (для архитектора)

- **Схема БД:** конфликт между Alembic-миграциями demoday и `schema.sql` bonus. Требуется аккуратная миграция расширения схемы
- **pgvector:** добавление расширения в production-БД, ребилд индексов
- **Embeddings:** все ~330 проектов нужно проэмбеддить (Gemini 3072d). Стоимость и время на первый запуск
- **Параллельный запуск бота + scheduler через один token:** Telegram allow только один long-poll на token. Если бот в новом процессе делает polling, scheduler НЕ может тоже polling, только send. Нужен webhook или явное разделение

### Продуктовые риски

- **Регрессия admin-сценариев:** удаление кода старого бота может затронуть admin-сервисы (например, `app/services/guest/profiling_service.py` импортируется из админских модулей)
- **Поведение бота меняется:** гость, привыкший к старому UX (PTB ConversationHandler), увидит новый агент с другими экранами. Допустимо (история синтетика)
- **Messaging / SupportChat:** требуют доработки нового бота, чтобы админка осталась рабочей. Если архитектор выберет неудачное решение -- админка отвалится

### Организационные риски

- Объём работы значительный: миграция схемы + перенос/переключение бота + интеграция scheduler + интеграция Messaging/SupportChat + развёртывание `llm-agent-platform`. Нужна декомпозиция на фазы

---

## Следующие шаги

1. Подтвердить бриф у заказчика
2. Передать **архитектору** для технической проработки (закрытие Open Questions, выбор схемы интеграции, план миграции БД)
3. После архитектурного решения -- декомпозиция на User Stories / задачи (User Story Mapping)

---

## История изменений

| Версия | Дата | Изменения |
|---|---|---|
| 1.0 | 2026-05-03 | Первая версия брифа после discovery-сессии с заказчиком |
