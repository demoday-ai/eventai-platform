# AI Talent Camp 2026 -- Команда "ЯСНОПОНЯТНО"

## О кэмпе

AI Talent Camp -- кэмп по AI, 33 идеи-проекта, над каждой работает команда. Команды получают выделенные VM в Yandex Cloud (4 vCPU, 8GB RAM, 65GB SSD, Ubuntu 22.04) с доменом `teamXX.camp.aitalenthub.ru`. Наш проект -- #10 AI-агент-куратор DemoDay.

## Продукт: AI-агент-куратор DemoDay (AI-first Unconference Navigator)

**Автор идеи:** Дмитрий Ботов (@dmbotov)

### Проблема

На Demo Day много проектов и треков (~330 проектов: 215 Demo Day в 6 залах + 115 Research в 4 залах), а времени у гостей мало: гость физически успевает посетить <20% проектов. Сложно быстро найти "свои" доклады/демо, сравнить проекты по нужным критериям и организовать содержательный Q&A. В итоге часть релевантных проектов остаётся незамеченной, а фоллоу-ап после мероприятия хаотичный.

### Целевая аудитория

Внешние гости Demo Day: индустриальные партнёры/заказчики, инвесторы, HR/нанимающие менеджеры, менторы и жюри; также core-команда Хаба (организаторы).

### Решение

Участники заранее загружают питч-дек, демо-видео/линк, репозиторий, артефакты. Агент добавляет метаданные (теги, трек). Гость приходит в чат к агенту и формулирует интерес (задачи/отрасль/стек/стадия/формат партнёрства). Агент:

1. **Персональная программа** -- собирает подборку проектов + короткие брифы по каждому
2. **Q&A-помощник** -- предлагает вопросы для Q&A и матрицу сравнения под запрос гостя
3. **Организация встреч** -- слоты 1:1 или групповой Q&A с авторами проектов
4. **Follow-up пакет** -- конспект, обратная связь, контакты, next steps, шаблоны писем/LOI

### Данные прошлого Demo Day (валидация масштаба)

Анализ реального Demo Day (22-23 января 2026, 2 дня, 2 трека):

**День 1:** ~110 проектов, 6 параллельных залов (10:30-19:30)
- Залы условно тематические (EdTech, HR/Recsys, Агенты, NLP/CV, ML в пром., FinTech)
- Каждый проект -- 15 мин (презентация + Q&A)
- Модераторы в каждом зале

**День 2:** ~105 проектов, 4 зала (14:00-19:30), **два формата:**
- Залы 1-2: "Презентация проектов перед **бизнес-партнёрами**"
- Залы 3-4: "**Прожарка** проектов" (жёсткий разбор, критика)
- Утром: секция [AI]битуриент (12:30-14:00)

**AI Talent Conf (Research)** -- параллельно День 2:
- ~115 проектов, 4 зала, постерные сессии (11:00-17:00)
- Залы 1-2: общий research, залы 3-4: аспиранты (12 чел)

**Итого ~330 проектов.** Тематики: NLP (доминирует), Автономные агенты, EdTech, FinTech, ML в промышленности, CV, Security, ASR, LLM/VLM, RL, BioTech, MedTech и др.

**Ключевая метрика:** гость может посетить максимум 16% проектов (34 из 212 на Demo Day). NLP-фанат пропустит 68% NLP-проектов из-за параллельности.

### Существующее решение: Demo-Hero (@jugru_conf_bot)

На прошлых Demo Day использовался бот Demo-Hero. Его функционал:
- Онбординг: пол + "чем занимаешься" (поверхностное профилирование)
- Tinder-механика: показывает пары докладов, выбираешь какой нравится
- Маршрут: формирует персональный маршрут (работал с багами)
- Расписание: присылает полное расписание перед мероприятием
- Фидбэк: после доклада спрашивает оценку
- Post-event: оценка конференции 1-5

Слабые стороны Demo-Hero:
- Нет глубокого профилирования под задачи гостя
- Tinder-пары медленные и не масштабируются на 330 проектов
- Нет Q&A помощника и матрицы сравнения
- Нет follow-up пакета (контакты, LOI, next steps)
- Нет организации встреч 1:1
- Нет работы с разными сегментами ЦА (инвесторы vs HR vs партнёры)

## Команда

- **Дмитрий Горбунов** (@grbn_dima) -- хастлер/хипстер. Тимлид, бизнес, продукт, UX/UI
- **Анастасия Гапеева** -- хипстер/хакер. UX/UI, фронтенд, разработка
- **Иван Александров** -- хакер/хастлер. Разработка, техническая реализация, бизнес-логика
- **Claude** -- AI-ассистент команды. Подключён к чату через Telegram-бота (`telegram-log/`).

## Репозиторий

**Основной:** https://github.com/AI-Talent-Camp-2026/demoday-ai (единый монорепо)

| Папка | Назначение |
|-------|-----------|
| `docs/` | Документация, спецификация, артефакты discovery |
| `data/` | Данные: экспертный маппинг, тестовые данные |
| `data/test/` | Анонимизированные Excel-файлы DD для тестирования и демо |
| `scripts/` | Утилиты (анонимизация, обработка данных) |
| `telegram-log/` | Telegram-бот для логирования чата команды |

**Инфраструктура кэмпа:** https://github.com/AI-Talent-Camp-2026/ai-talent-camp-2026-infra

## Инфраструктура кэмпа

VM в Yandex Cloud, управляется Terraform. Подключение через SSH bastion (`bastion.camp.aitalenthub.ru`).

- **Edge/NAT VM** -- единственная точка входа, Traefik (reverse proxy), Xray (AI API proxy), NAT
- **Team VMs** (4 vCPU, 8GB RAM, 65GB SSD) -- по одной на команду, private subnet
- **Домены:** `teamXX.camp.aitalenthub.ru`
- **Номер команды и SSH-ключи:** ждём от оргов

## Документация

### `docs/00-research/` — Исследования и аналитика

| Документ | Описание |
|----------|----------|
| `demoday-analytics.md` | Аналитика прошлого Demo Day: масштаб, конфликты, сценарии, гипотезы |
| `past-demoday-projects.md` | Каталог ~330 проектов по залам и тематикам |
| `demo-hero-example.md` | Лог взаимодействия с Demo-Hero + анализ UX-проблем |

### `docs/01-discovery/` — Воркшоп 1: AI-First Customer Discovery

_Воркшоп: Андрей Кузьминых (Andre AI Technologies), Вадим Чижков (OneCell.ai). Артефакты n8n-пайплайна Product Discovery + реальное CustDev-интервью._

| Документ | Описание |
|----------|----------|
| `customer-discovery.md` | Опросник для интервью с организаторами Demo Day + заметки по итогам |
| `interview-transcript.md` | Транскрипт интервью #1 с организатором (ElevenLabs Scribe v2) |
| `lean-canvas.md` | Lean Canvas v2.0 (5 сегментов, все 4 интервью) |
| `rice-matrix.md` | RICE-матрица v4.0: 17 гипотез, 4 интервью |
| `customer-journeys.md` | Клиентские пути AS-IS → TO-BE по 5 ролям |
| `icp.md` | Ideal Customer Profile по 5 сегментам |
| `pain-map.md` | Pain Map: 13 болей по 5 сегментам |
| `jtbd.md` | Jobs-To-Be-Done: 10 jobs с forces-анализом и desired outcomes |
| `vpc.md` | Value Proposition Canvas по 5 сегментам |

### `docs/02-specification/` — Воркшоп 2: Specification-Driven Development

_Воркшоп: Василий Рассказов (X5). Фреймворк: Discovery Kit v1.1.7. От идеи продукта до ТЗ._

| Документ | Описание | Статус |
|----------|----------|--------|
| `01-brief.md` | Бриф проекта v3.0: проблема, цели, ограничения, контекст | DONE |
| `02-user-story-map.md` | User Story Map v2.1: backbone → 15 epics → 21 stories | DONE |
| `03-user-journey-map.md` | User Journey Map v1.1 (Mermaid) | DONE |
| `04-nfr.md` | Нефункциональные требования (Performance, Security, Scalability) | DONE |
| `06-information-architecture.md` | Информационная архитектура v1.1: sitemap, навигация, 5 ролей, Q&A-helper | DONE |
| `07-c4-architecture.md` | C4-диаграмма v1.1: Context + Container, 5 persons, Xray proxy | DONE |
| `08-er-diagram.md` | ER-диаграмма v1.1: 24 сущности (+business_profiles, +qa_suggestions) | DONE |
| `09-sequence-diagrams.md` | Sequence-диаграммы v1.1: 8 сценариев (+Q&A, +бизнес-профилирование) | DONE |
| `10-api-inventory.md` | Инвентаризация API v1.1: 72 endpoint (+business, +Q&A, +guest-subtype) | DONE |
| `personas/` | Персоны: 5 ролей + anti-persona + early adopter | DONE |
| `wireframes/` | ASCII-вайрфреймы: 4 экрана бота | DONE |
| `diagrams/` | Journey-диаграммы (PNG) | DONE |

## Тестовые данные (`data/test/`)

Анонимизированные данные реального DD (22-23 января 2026). Используются для тестирования и демо.

| Файл | Содержимое |
|------|-----------|
| `experts_22jan_anon.xlsx` | Оценки экспертов День 1: 18 листов, 605 блоков, 6 залов |
| `experts_23jan_anon.xlsx` | Оценки экспертов День 2: 29 листов, 182 блока (AITalConf + Бизнес + Прожарка) |
| `checkpoint3_anon.xlsx` | 3 контрольный рубеж: 1135 записей, self/peer/mentor review, 80 колонок |
| `checkpoint12_anon.xlsx` | 1-2 контрольные рубежи: регистрация проектов, треки, команды |

**Ключевые цифры:** 330 проектов, 31 комната, 7 критериев оценки (1-3, веса 10-20%), средний балл 2.41/3.0, 63% проектов оценены 1 экспертом.

**Система оценивания:** 7 критериев (Актуальность, Практ.значимость, Новизна, Импакт, R&D, Масштабирование, + 7-й зависит от формата). Критерий 7: Research → Публичность, Demo Day → Качество реализации, Бизнес → Валидация.

## Рабочие соглашения

- Основной язык общения: русский
- Чат команды: Telegram, группа "ЯСНОПОНЯТНО"

### Разработка и тестирование

**TDD-подход для новых фич:**
1. Сначала пишем тесты (описываем ожидаемое поведение)
2. Запускаем тесты — они падают (red)
3. Пишем минимальный код для прохождения тестов (green)
4. Рефакторим при необходимости (refactor)

**Frontend (React + Vitest):**
- Тесты для компонентов: `@testing-library/react`
- Тесты для API: `axios-mock-adapter`
- Запуск: `npm test`
- Coverage: `npm run test:coverage`

**Backend (Python + pytest):**
- Тесты для API: `pytest` + `httpx.AsyncClient`
- Моки: `pytest-mock`, `unittest.mock`
- Запуск: `pytest`
- Coverage: `pytest --cov`

**Стандарт покрытия:**
- Новые фичи: минимум 80% coverage
- Критические пути: 100% coverage
- Тесты коммитятся вместе с кодом

## Active Technologies

**Backend:**
- Python 3.12+ + FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, asyncpg
- PostgreSQL 16
- httpx, python-multipart, OpenRouter API
- APScheduler 3.10+ (CronTrigger + IntervalTrigger)

**Frontend:**
- React 19 + TypeScript + Vite
- TanStack Query (react-query) для API
- Tailwind CSS + shadcn/ui
- React Router v7
- Vitest + Testing Library для тестов

## Recent Changes
- 001-onboarding: Added Python 3.12+ + FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, asyncpg
- 002-project-clustering: Added httpx, python-multipart, OpenRouter API integration, 6 new DB tables (projects, tags, project_tags, clustering_runs, rooms, room_projects), LLM-based clustering, seed data (400 projects from checkpoint forms)
- 005-dd-reminders: Added APScheduler 3.10+ (CronTrigger + IntervalTrigger), 3 new DB tables (schedule_slots, notifications, schedule_change_logs), schedule auto-generation from clustering, eve-of-DD and pre-slot reminders, timing shift notifications with batching
- 016-organizer-web-admin: Added frontend (React + Vite + TypeScript + Tailwind + shadcn/ui), Phase 1 Dashboard with metrics API (GET /api/v1/admin/dashboard), TanStack Query, auto-refresh, alerts, 10 tests (Vitest + Testing Library)
