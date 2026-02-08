<!--
## Sync Impact Report

**Version**: 1.0.0 → 1.1.0
**Bump type**: MINOR — tech stack correction, governance expansion, principle language tightening
**Date**: 2026-02-02

### Modified Principles
1. I. Telegram-First — language tightened (MUST/SHOULD), no semantic change
2. II. AI-Augmented, Human-Approved — language tightened, no semantic change
3. III. Data-Driven — language tightened, no semantic change
4. IV. Pragmatic Development — language tightened, no semantic change

### Modified Sections
- Технологический стек: LangChain/OpenAI SDK → OpenRouter API (GPT-4.1, Claude) per Brief v3.0
- Инфраструктура: added team12 domain, SSH bastion details
- Governance: expanded — added amendment procedure, versioning policy, compliance review, document hierarchy

### Added Sections
- Governance > Иерархия документов
- Governance > Процедура изменений
- Governance > Политика версионирования
- Governance > Compliance review

### Removed Sections
- None

### Template Sync Status
- `.specify/templates/plan-template.md` — ✅ Compatible (Constitution Check maps to 4 principles)
- `.specify/templates/spec-template.md` — ✅ Compatible (user stories, requirements, success criteria)
- `.specify/templates/tasks-template.md` — ✅ Compatible (phase structure, path conventions)
- `.specify/templates/commands/*.md` — ✅ N/A (directory empty — commands are in `.claude/commands/`)

### Follow-up TODOs
- None. All placeholders resolved.
-->

# DemoDay AI Navigator — Constitution

**Version**: 1.1.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-02-02

---

## Принципы разработки

### I. Telegram-First

- Telegram Bot API — единственный канал взаимодействия с пользователями. Система НЕ ДОЛЖНА требовать установки дополнительных приложений.
- Все действия пользователя ДОЛЖНЫ выполняться через inline-кнопки. Свободный текстовый ввод — только для профилирования (гость, бизнес) и комментариев (эксперт).
- Бот ДОЛЖЕН поддерживать 5 ролей с адаптивным интерфейсом: Организатор, Студент, Эксперт, Гость (с подтипами: Абитуриент / AI-практик / Другое), Бизнес/партнёр.
- Ограничения Telegram Bot API ДОЛЖНЫ учитываться в архитектуре: 30 msg/sec (очередь обязательна), 4096 символов/сообщение, 64 байта callback data.
- **Обоснование:** CustDev #1 (организатор): "Я бы не пользовалась никаким приложением." CustDev #2 (эксперт): "Неудобно себе отдельно ставить для демо-дня."

### II. AI-Augmented, Human-Approved

- AI ДОЛЖЕН предлагать решения (кластеризация, рекомендации, Q&A-подсказки, предобработка ОС). Человек ДОЛЖЕН утверждать критические действия.
- Организатор ДОЛЖЕН модерировать: утверждение расписания (кластеризация), рассылку ОС студентам, подборки для бизнес-партнёров (при необходимости).
- Q&A-подсказки ДОЛЖНЫ генерироваться только для гостей и бизнес-партнёров. Эксперты НЕ ДОЛЖНЫ получать подсказки вопросов — CustDev #2: "Вопросы от человека."
- Контакты ДОЛЖНЫ передаваться только с согласия обеих сторон (152-ФЗ). CustDev #3 (Олег): "Не всем ребятам будет интересно."
- CRUD-функции (подтверждения, оценки, напоминалки) НЕ ДОЛЖНЫ зависеть от LLM API. При недоступности LLM — graceful degradation: AI-фичи показывают "AI-сервис временно недоступен", остальное работает.
- **Обоснование:** Brief v3.0: "Бот не заменяет организатора." NFR: graceful degradation при отказе LLM.

### III. Data-Driven

- Реальные данные прошлого DD ДОЛЖНЫ использоваться для тестирования и валидации: 333 проекта, 319 экспертов (294 в базе, 76 подтверждённых), 733 студента.
- Тестовые данные ДОЛЖНЫ быть анонимизированы и храниться в `data/test/`.
- Кластеризация ДОЛЖНА выполняться по тематикам (NLP, CV, Agents, FinTech, ...), НЕ по трекам (EdTech, стартап, индустрия, наука). Треки — формат обучения студента.
- Оценка проектов — 7 критериев (1-3 балла, веса 10-20%), взвешенный итог 0-100%.
- Для демо — данные предзагружены. Продакшен-интеграция с Google Sheets / формами — Release 1.1.
- **Обоснование:** Аналитика прошлого DD (`docs/00-research/demoday-analytics.md`): гость видит максимум 16% проектов.

### IV. Pragmatic Development

- Демо 6 февраля 2026. MVP ДОЛЖЕН покрывать все 5 ролей end-to-end.
- Приоритизация по RICE v4.0 (15 фич): напоминалки (780) > подтверждения (495) > кластеризация (335) > предобработка ОС (264) > единая точка входа (88).
- YAGNI: минимум абстракций. Не проектировать под гипотетические будущие требования.
- Предзагруженные данные для демо. Продакшен-интеграции (Google Sheets, GitHub API) — Release 1.1.
- Команда: 3 человека + Claude. Claude генерирует код, команда интегрирует и готовит демо-сценарий.
- **Обоснование:** Brief v3.0: "5 дней от старта." RICE-матрица: `docs/01-discovery/rice-matrix.md`.

---

## Технологический стек

### Сервер (Python)
- **Python 3.12+**
- **FastAPI** — REST API + WebSocket
- **SQLAlchemy 2.0** + **Alembic** — ORM + миграции
- **PostgreSQL 16** — основная БД
- **python-telegram-bot** — Telegram Bot API
- **OpenRouter API** (GPT-4.1, Claude) — LLM-интеграция через Xray proxy кэмпа

### Клиент (Admin Console — если хватит ресурсов)
- **React 18 + TypeScript**
- **Vite**
- **Tailwind CSS**
- **React Query** + **Zustand**

### Инфраструктура
- **Docker** + **Docker Compose**
- **Yandex Cloud VM** (4 vCPU, 8GB RAM, 65GB SSD, Ubuntu 22.04)
- **Домен:** `team12.camp.aitalenthub.ru`
- **Traefik** — reverse proxy (на Edge VM кэмпа)
- **Xray** — AI API proxy (на Edge VM кэмпа)
- **SSH bastion:** `bastion.camp.aitalenthub.ru`
- **GitHub Actions** — CI/CD

---

## Coding Standards

- **Ruff** для линтинга и форматирования Python
- **ESLint + Prettier** для клиента (если реализуется)
- **Conventional commits:** `feat/fix/docs/chore(scope): message`
- **OpenAPI 3.0** — документация API (72 endpoint, `docs/02-specification/10-api-inventory.md`)
- Тесты ДОЛЖНЫ покрывать критичные пути: кластеризация, матчинг экспертов, рассылка напоминалок
- Секреты (токены бота, API-ключи) НЕ ДОЛЖНЫ попадать в систему контроля версий. Хранить в переменных окружения.

---

## Архитектура

```
Telegram Bot <-> Core API <-> PostgreSQL
                   |               |
            Matching & Q&A   Notification Worker
                   |
             LLM (Xray proxy)
```

| Контейнер | Назначение |
|-----------|-----------|
| **Telegram Bot** | Диалоговый интерфейс для 5 ролей |
| **Core API** | Бизнес-логика, REST (FastAPI) |
| **Matching & Q&A** | Рекомендации, кластеризация, Q&A-подсказки, бизнес-матчинг |
| **Notification Worker** | Async: напоминалки, follow-up, рассылка ОС |
| **Database** | PostgreSQL 16 — пользователи, проекты, оценки, статусы |
| **Admin Console** | Веб-дашборд для организаторов (опционально) |

Полная C4-диаграмма: `docs/02-specification/07-c4-architecture.md`

---

## Governance

### Иерархия документов

1. **Constitution** (этот файл) — принципы, стек, архитектурные решения
2. **Brief** (`docs/02-specification/01-brief.md`) — бизнес-контекст, ограничения, приёмка
3. **USM** (`docs/02-specification/02-user-story-map.md`) — user stories, epics, releases
4. **NFR** (`docs/02-specification/04-nfr.md`) — нефункциональные требования
5. **C4 / ER / API** (`docs/02-specification/07-10`) — техническая спецификация

### Процедура изменений

1. Инициатор предлагает изменение в чате команды ("ЯСНОПОНЯТНО")
2. Обсуждение с командой (включая Claude)
3. Правка документа
4. Коммит с conventional commit message: `docs: amend constitution to vX.Y.Z (описание)`

### Политика версионирования

- **MAJOR** (X.0.0): удаление или переопределение принципов, несовместимые изменения governance
- **MINOR** (0.X.0): новый принцип/секция, существенное расширение guidance
- **PATCH** (0.0.X): уточнения формулировок, опечатки, косметические правки

### Compliance review

- При создании `/speckit.plan` — Constitution Check ДОЛЖЕН пройти до Phase 0 research
- При изменении конституции — проверка консистентности шаблонов `.specify/templates/`
- AI (Claude) — полноправный участник команды, подключён через Telegram-бот и CLI
