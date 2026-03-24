# AGENTS.md

Этот документ фиксирует правила работы агентов в репозитории EventAI (`demoday-core`). Основано на
README.md, CLAUDE.md, developer-manifest.md и текущей структуре репозитория.

## Контекст проекта
- EventAI — AI-платформа для организаторов событий с ботом и админкой. Основной validated use case
  в репозитории — Demo Day / AI Talent Camp: кластеризация проектов, подбор экспертов,
  персональные рекомендации гостям, Q&A-помощник, follow-up и операционные инструменты для команды.
- AI Talent Camp 2026, команда "ЯСНОПОНЯТНО".
- Основные сегменты: организаторы, эксперты/менторы, бизнес/партнеры, гости, участники проектов.

## Источники контекста
- `CLAUDE.md` — полный контекст по продукту, данным Demo Day, инфраструктуре и стеку.
- `README.md` — краткий обзор продукта и карта репозитория.
- `developer-manifest.md` — роли, правила взаимодействия, требования к Issue/PR.
- `docs/` — исследования, discovery, спецификации, персоны, схемы, вайрфреймы.

## Роли и правила взаимодействия
### Разработчик
- Следует правилам из `AGENTS.md`, `CLAUDE.md` и др.
- Пишет код и тесты, ведет BDD/TDD процесс.
- Делает осмысленные коммиты и обновляет документацию.
- Не допускает "спагетти" кода.

### Ревьювер кода
- Не пишет код и не вносит правки в файлы.
- Проверяет качество кода и риски регрессий.
- Создает issues с замечаниями и рекомендациями.

### Ревьювер тестов
- Не правит код и тесты.
- Проверяет, что тесты подтверждают поведение, а не реализацию.
- Допускает "красные" тесты, если это отражает реальное состояние задачи.
- Создает issues с замечаниями и рекомендациями.

## Рабочие соглашения
- Основной язык общения: русский.
- Командный чат: Telegram (группа "ЯСНОПОНЯТНО").
- Если требования неясны — остановиться и открыть issue с вопросами.
- Не расширять scope задачи без новой issue.
- Все замечания ревьюеров оформляются отдельными issues.
- Если обнаружен баг вне задачи — зафиксировать в issue и не чинить в текущем PR.

## Репозиторий и данные
- `backend/` — FastAPI API, Telegram-бот, Celery worker, модели, сервисы, миграции Alembic.
- `frontend/` — React/Vite админка для организаторов.
- `docs/` — исследования, discovery, спецификации и артефакты продукта.
- `data/` — данные и анонимизированные тестовые файлы (`data/test/`).
- `scripts/` — утилиты обработки данных.
- `telegram-log/` — бот для логирования командного чата.

## Стек и ключевые компоненты
- Backend: Python 3.12+, FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, asyncpg.
- Frontend: React 19, TypeScript, Vite, TanStack Query, Tailwind CSS.
- Infra: PostgreSQL 16, Redis, RabbitMQ, Qdrant, Celery, APScheduler, Docker Compose.
- AI: OpenRouter API и Gemini embeddings для кластеризации, профилирования и рекомендаций.
- Входной модуль API: `backend/app/main.py`.

## Запуск и конфигурация
- Docker окружение описано в `docker-compose.yml` и поднимает `db`, `redis`, `rabbitmq`,
  `qdrant`, `backend`, `worker`, `flower`, `frontend`.
- Backend контейнер стартует `uvicorn app.main:app`, worker использует Celery.
- Конфигурация через `backend/.env` (см. `backend/app/config.py`).
  Основные поля: `database_url`, `bot_token`, `bot_mode` (polling/webhook),
  `organizer_telegram_ids` (через запятую), `secret_key`, `webhook_url`,
  `openrouter_api_key`, `openrouter_api_keys`, `openrouter_base_url`, `openrouter_model`,
  `rabbitmq_url`, `redis_url`, `qdrant_url`.

## Качество и тесты
- Issue: содержит Why/What/How/Acceptance Criteria, примеры ввода/вывода, ограничения.
- PR: краткое описание, сценарии BDD/TDD, команда запуска тестов, статус (Red/Green).
- Минимум один BDD/TDD сценарий на задачу; тесты проверяют поведение.
- Инструменты качества: pytest, pytest-asyncio, ruff (см. `backend/pyproject.toml`).
