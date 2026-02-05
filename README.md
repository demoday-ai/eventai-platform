# EventAI — AI-платформа для мероприятий

[![CI](https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml)
[![CD](https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml/badge.svg)](https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml)
![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

![Event Management](https://images.unsplash.com/photo-1540575467063-178a50c2df87?q=80&w=2000&auto=format&fit=crop)

**AI Talent Camp 2026 | Проект #10**
Разработано в рамках магистратуры «Искусственный интеллект» ИТМО

> AI-платформа для персонализации мероприятий с параллельными треками: Demo Day, конференции, хакатоны, выставки. Telegram-бот генерирует персональную программу за 2 минуты диалога. Админ-панель автоматизирует кластеризацию проектов, распределение экспертов, расписание и напоминания.

**🌐 Live Demo:** https://team12.camp.aitalenthub.ru
**🤖 Telegram Bot:** [@demoday_ai_talent_hub_test_bot](https://t.me/demoday_ai_talent_hub_test_bot)

## Содержание

- [Проблема](#проблема)
- [Решение](#решение)
- [Качество рекомендаций](#качество-рекомендаций)
- [Архитектура](#архитектура)
- [Стек технологий](#стек-технологий)
- [Быстрый старт](#быстрый-старт)
- [Разработка](#разработка)
- [API Endpoints](#api-endpoints)
- [Тестирование](#тестирование)
- [Telegram Bot](#telegram-bot)
- [Customer Discovery](#customer-discovery)
- [Команда](#команда)

---

## Проблема

На Demo Day ~330 проектов в 6-10 параллельных залах. Ключевые боли:

- **Расфокус экспертов** — непонятно, куда идти, чтобы принести ценность
- **Хаос с расписанием** — составляется вручную, 80 студентов не попали за ночь до DD
- **Низкая явка** — конверсия из приглашений ~40-50% из-за позднего расписания
- **Эксперты вслепую** — нет контекста о проектах заранее
- **Бизнес не находит релевантное** — нет автоматизированного подбора
- **Гости видят <20% проектов** — пропускают интересное из-за параллельности

> "Это пипец! Если вы упростите этот ужас, я буду благодарна." — Инна, организатор Demo Day

---

## Решение

### Для гостей и партнёров
Telegram-бот с персонализацией:
- **2-минутное профилирование** — AI-диалог извлекает интересы
- **Персональный топ проектов** — рейтинг релевантности по профилю
- **Q&A-помощник** — 3-5 вопросов к каждому проекту
- **Сравнение проектов** — таблица отличий 2-5 проектов
- **Маршрут по залам** — оптимальный порядок посещения
- **Контакт с авторами** — запрос через бота с согласия

### Для организаторов
Админ-панель с автоматизацией:
- **AI-кластеризация** — 330 проектов → 6-10 тематических залов (LLM)
- **Распределение экспертов** — автоматический подбор по тегам
- **Генерация расписания** — слоты по 15 минут, конфликты исключены
- **Подтверждение участия** — студенты и эксперты подтверждают через бота
- **Напоминания** — eve-of-DD, pre-slot, сдвиги тайминга
- **Аналитика покрытия** — кто из экспертов где, пробелы, эскалации
- **Оценивание** — эксперты ставят оценки через бота (не Google Таблицы)

---

## Качество рекомендаций

### Метрики

Оценка качества рекомендательной системы на 10 реальных профилях (5 гостей + 5 бизнес-партнёров), экспертные аннотации по 330 проектам:

| Метрика | @5 | @15 | Что измеряет |
|---------|-----|------|----------|
| **NDCG** | 0.79 | 0.82 | Релевантные проекты в топе списка (качество ранжирования) |
| **Precision** | 0.68 | 0.71 | Сколько из показанных проектов действительно интересны гостю |
| **Recall** | 0.52 | 0.78 | Сколько подходящих проектов система нашла из всех возможных |

### Как это работает

```
Профиль гостя → Поиск по тегам → AI-ранжирование → Топ-15 рекомендаций
                                       ↓
                        Проверка экспертами (оценки 0-3)
```

**Пайплайн рекомендаций:**
1. **Поиск по тегам** — находим проекты с совпадающими тегами и ключевыми словами
2. **Анализ текста** — ищем смысловые совпадения в описании профиля и проектов
3. **AI-ранжирование** — Claude/GPT переранжирует топ-20 с учётом контекста и нюансов профиля
4. **Валидация** — сравниваем результаты с оценками экспертов (релевантность ≥ 2 из 3)

**Данные:**
- 330 проектов Demo Day (NLP, CV, Agents, EdTech, FinTech, Industrial)
- 10 персон: guest_1-5 (соискатели, разработчики), business_1-5 (HR, инвесторы, партнёры)
- 1085 пар "персона-проект" с экспертной оценкой релевантности

**Код:** `data/eval/evaluate.py` (branch: `feature/eval`)

---

## Архитектура

### Структура проекта

```
demoday-core/
├── frontend/                          # React 19 + TypeScript + Vite
│   ├── src/
│   │   ├── pages/                     # 32 страницы
│   │   │   ├── Landing.tsx            # Публичный лендинг (72 KB)
│   │   │   ├── Dashboard.tsx          # Дашборд организатора
│   │   │   ├── DataImport.tsx         # Загрузка CSV/Excel
│   │   │   ├── Clustering.tsx         # AI-кластеризация
│   │   │   ├── ExpertMatching.tsx     # Распределение экспертов
│   │   │   ├── Schedule.tsx           # Генерация расписания
│   │   │   ├── Coverage.tsx           # Аналитика покрытия
│   │   │   ├── Notifications.tsx      # Управление уведомлениями
│   │   │   └── ...                    # + 24 страницы
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui компоненты
│   │   │   ├── layout/                # Навигация, AppLayout
│   │   │   └── import/                # FileUpload, ImportSummary
│   │   ├── lib/
│   │   │   ├── api-client.ts          # HTTP клиент (axios)
│   │   │   └── utils.ts               # Утилиты
│   │   └── hooks/                     # Custom React hooks
│   ├── Dockerfile                     # Multi-stage build + nginx
│   └── package.json                   # Dependencies
│
├── backend/                           # FastAPI + Python 3.12
│   ├── app/
│   │   ├── api/                       # 13 роутеров, 60+ endpoints
│   │   │   ├── admin.py               # Дашборд, метрики (17.9 KB)
│   │   │   ├── projects.py            # CRUD проектов
│   │   │   ├── experts.py             # Управление экспертами (15.5 KB)
│   │   │   ├── guests.py              # Профилирование гостей
│   │   │   ├── schedule.py            # Расписание и слоты
│   │   │   ├── reminders.py           # Напоминания
│   │   │   ├── leads.py               # Форма заявок (→ Telegram)
│   │   │   └── ...
│   │   ├── bot/                       # Telegram bot handlers
│   │   │   ├── handlers/              # 18 handler modules
│   │   │   │   ├── start.py           # Онбординг (5 ролей)
│   │   │   │   ├── guest_profiling.py # Профилирование гостей
│   │   │   │   ├── expert_assignment.py # Назначение экспертов
│   │   │   │   ├── briefing.py        # Брифинг экспертов
│   │   │   │   ├── reminder.py        # Отправка напоминаний
│   │   │   │   └── ...
│   │   │   ├── keyboards.py           # Telegram клавиатуры
│   │   │   └── app.py                 # Bot initialization
│   │   ├── models/                    # SQLAlchemy models (34 entities)
│   │   │   ├── user.py, role.py       # RBAC
│   │   │   ├── project.py, tag.py     # Проекты и теги
│   │   │   ├── expert.py              # Эксперты
│   │   │   ├── guest_profile.py       # Профили гостей
│   │   │   ├── schedule_slot.py       # Слоты расписания
│   │   │   └── ...
│   │   ├── services/                  # 30+ бизнес-логики
│   │   │   ├── clustering_service.py  # LLM кластеризация
│   │   │   ├── profiling_service.py   # AI профилирование
│   │   │   ├── matching_service.py    # Подбор экспертов
│   │   │   ├── qa_service.py          # Q&A генерация
│   │   │   ├── schedule_service.py    # Генерация расписания
│   │   │   ├── reminder_service.py    # Логика напоминаний
│   │   │   ├── llm_client.py          # OpenRouter API
│   │   │   └── ...
│   │   └── main.py                    # FastAPI + APScheduler
│   ├── alembic/                       # DB migrations
│   ├── tests/                         # pytest + pytest-asyncio
│   ├── Dockerfile                     # Python 3.12 image
│   └── pyproject.toml                 # Dependencies
│
├── data/
│   └── seed/                          # 400 тестовых проектов
│
├── docs/
│   ├── 00-research/                   # Исследования прошлого DD
│   │   ├── demoday-analytics.md       # Масштаб, конфликты
│   │   └── past-demoday-projects.md   # ~330 проектов
│   ├── 01-discovery/                  # Customer Discovery
│   │   ├── lean-canvas.md             # 5 сегментов
│   │   ├── rice-matrix.md             # 17 гипотез, 4 интервью
│   │   └── interview-transcript*.md   # 5 транскриптов
│   └── 02-specification/              # Spec-driven development
│       ├── 02-user-story-map.md       # 15 epics, 21 stories
│       ├── 07-c4-architecture.md      # C4 diagram
│       ├── 08-er-diagram.md           # 34 entities
│       └── 10-api-inventory.md        # 72 endpoints
│
├── docker-compose.yml                 # Development
├── docker-compose.prod.yml            # Production (Traefik)
├── DEPLOY.md                          # Production deployment guide
└── CLAUDE.md                          # Context для Claude Code
```

---

## Стек технологий

### Backend
| Компонент | Версия | Назначение |
|-----------|--------|-----------|
| Python | 3.12+ | Язык программирования |
| FastAPI | 0.115+ | REST API framework |
| uvicorn | 0.32+ | ASGI server |
| SQLAlchemy | 2.0+ | ORM (async) |
| PostgreSQL | 16 | База данных |
| Alembic | 1.14+ | Миграции БД |
| python-telegram-bot | 21.x | Telegram bot library |
| APScheduler | 3.10+ | Scheduled jobs (reminders) |
| httpx | 0.27+ | Async HTTP client |
| OpenRouter API | — | LLM доступ (Claude/GPT) |
| email-validator | 2.0+ | Валидация email |
| pydantic-settings | 2.0+ | Конфигурация |
| python-jose | 3.3+ | JWT токены |

### Frontend
| Компонент | Версия | Назначение |
|-----------|--------|-----------|
| React | 19 | UI framework |
| TypeScript | 5.9 | Типизация |
| Vite | 7.2 | Build tool |
| React Router | 7.13 | Routing |
| TanStack Query | 5.90 | Server state |
| Tailwind CSS | 4.1 | Styling |
| shadcn/ui | — | UI components |
| axios | 1.13 | HTTP client |
| lucide-react | 0.563 | Icons |
| Vitest | 4.0 | Testing |

### Инфраструктура
| Компонент | Назначение |
|-----------|-----------|
| Docker Compose | Контейнеризация |
| PostgreSQL 16-alpine | БД (с volume для persistence) |
| nginx | Статика фронтенда |
| Traefik | Reverse proxy + SSL (production) |
| Yandex Cloud VM | Хостинг (4 vCPU, 8 GB RAM) |

---

## Быстрый старт

### 1. Требования
- Docker + Docker Compose
- Node.js 18+ (для локальной разработки фронтенда)
- Python 3.12+ (для локальной разработки бэкенда)

### 2. Клонировать репозиторий
```bash
git clone https://github.com/AI-Talent-Camp-2026/demoday-ai.git
cd demoday-ai
```

### 3. Настроить переменные окружения
```bash
cp backend/.env.example backend/.env
```

Заполнить обязательные переменные:
```env
BOT_TOKEN=your-telegram-bot-token
OPENROUTER_API_KEY=your-openrouter-key
ORGANIZER_TELEGRAM_IDS=123456789
TEAM_CHAT_ID=-100XXXXXXXXXX
TEAM_BOT_TOKEN=team-bot-token (optional)
```

### 4. Запустить
```bash
docker compose up -d --build
```

Сервисы:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000 (внутри контейнера)
- **Database:** localhost:5432 (внутри контейнера)

### 5. Инициализация БД
```bash
# Применить миграции
docker compose exec backend alembic upgrade head

# Загрузить тестовые данные (опционально)
docker compose exec backend python -m app.scripts.seed
```

---

## Разработка

### Frontend (локально)
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm test         # Запуск тестов
npm run build    # Production build
```

### Backend (локально)
```bash
cd backend
pip install -e .
pytest                     # Все тесты
pytest -m integration      # Только интеграционные
pytest --cov               # С coverage
```

### Миграции БД
```bash
# Создать миграцию
docker compose exec backend alembic revision --autogenerate -m "описание"

# Применить
docker compose exec backend alembic upgrade head

# Откатить
docker compose exec backend alembic downgrade -1
```

---

## Production Deploy

**Полная документация:** [DEPLOY.md](./DEPLOY.md)

### На AI Talent Camp VM (team12)

```bash
# Подключиться через bastion
ssh -F ~/.ssh/ai-camp/ssh-config team12

# Перейти в рабочую директорию
cd ~/workspace/demoday-ai

# Обновить код
git pull

# Развернуть
docker compose up -d --build

# Проверить логи
docker compose logs backend --tail 50
docker compose logs frontend --tail 50
```

**Доступ:**
- Landing: https://team12.camp.aitalenthub.ru
- Admin: https://team12.camp.aitalenthub.ru/login
- API: https://team12.camp.aitalenthub.ru/api/v1

### Production конфигурация

**Файл:** `docker-compose.prod.yml` (используется автоматически на сервере)

- Traefik reverse proxy с Let's Encrypt SSL
- Health checks для всех сервисов
- Автоматический restart (unless-stopped)
- Изолированная внутренняя сеть
- Логи с ротацией

---

## API Endpoints

### Public
- `GET /` — Landing page
- `POST /api/v1/leads` — Lead capture form

### Authentication
- `POST /api/v1/auth/login` — Login
- `POST /api/v1/auth/logout` — Logout

### Admin Dashboard
- `GET /api/v1/admin/dashboard` — Metrics
- `GET /api/v1/admin/coverage` — Coverage stats
- `POST /api/v1/admin/messaging/send` — Bulk messaging
- `POST /api/v1/admin/organizer` — Create organizer

### Projects
- `GET /api/v1/projects` — List projects
- `POST /api/v1/projects` — Create project
- `PUT /api/v1/projects/{id}` — Update project
- `DELETE /api/v1/projects/{id}` — Delete project

### Experts
- `GET /api/v1/experts` — List experts
- `POST /api/v1/experts` — Create expert
- `POST /api/v1/experts/{id}/assign` — Assign to room
- `POST /api/v1/experts/{id}/score` — Submit score

### Guests
- `POST /api/v1/profile` — Create/update profile
- `POST /api/v1/recommendations/{user_id}` — Generate recommendations
- `GET /api/v1/recommendations/{user_id}` — Get recommendations

### Schedule
- `GET /api/v1/schedule` — Get schedule
- `POST /api/v1/schedule/generate` — Auto-generate slots
- `POST /api/v1/schedule/notify` — Send schedule notifications

**Всего:** 60+ REST endpoints + Telegram bot webhook

---

## Тестирование

### Frontend Tests
```bash
cd frontend
npm test                 # Запуск всех тестов
npm run test:ui          # UI режим
npm run test:coverage    # С coverage
```

**Покрытие:**
- Dashboard, ExpertMatching, Settings — full coverage
- Landing, DataImport — частичное покрытие
- Всего: 16+ test файлов

### Backend Tests
```bash
cd backend
pytest                              # Все тесты
pytest -m integration               # Только интеграционные
pytest -m e2e                       # E2E (требуют credentials)
pytest --cov --cov-report=html      # HTML coverage отчет
```

**Целевое покрытие:**
- Новые фичи: 80%+
- Критические пути: 100%

---

## Telegram Bot

### Возможности бота

**Для всех ролей:**
- /start — Онбординг и выбор роли
- /help — Справка
- /settings — Настройки

**Для организаторов:**
- Управление событиями
- Рассылка сообщений
- Мониторинг покрытия

**Для экспертов:**
- Подтверждение участия
- Получение брифингов
- Оценивание проектов

**Для гостей:**
- Профилирование интересов
- Персональные рекомендации
- Q&A помощник
- Сравнение проектов

**Для студентов:**
- Подтверждение участия
- Получение фидбэка
- Контакт с партнёрами

### Настройка бота

1. Создать бота через [@BotFather](https://t.me/BotFather)
2. Получить токен
3. Добавить в `.env`:
```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
BOT_MODE=polling
```

4. Для уведомлений в чат команды:
```env
TEAM_CHAT_ID=-100XXXXXXXXXX
TEAM_BOT_TOKEN=team-bot-token
```

---

## Customer Discovery

**5 интервью, 4 сегмента, 17 гипотез**

| # | Респондент | Сегмент | Ключевой инсайт |
|---|-----------|---------|-----------------|
| 1 | Инна | Организатор | Расписание = хаос. 80 студентов не попали за ночь |
| 2 | Рустем Хакимуллин | Эксперт | Идёт вслепую. Нужен контекст за 1-2 дня |
| 3 | Олег Шатов | Бизнес | Из 330 проектов уверен в 15-20. Не масштабируется |
| 4 | Анастасия Гапеева | Гость | Посетила 5 из 330. Пропустила самый интересный |
| 5 | Дмитрий Ботов | Автор идеи | Расфокус экспертов + неравномерный фидбэк |

**Документация:**
- [docs/01-discovery/lean-canvas.md](./docs/01-discovery/lean-canvas.md) — Lean Canvas v2.0
- [docs/01-discovery/rice-matrix.md](./docs/01-discovery/rice-matrix.md) — RICE-матрица v4.0
- [docs/01-discovery/interview-transcript*.md](./docs/01-discovery/) — Транскрипты интервью

---

## Команда

**AI Talent Camp 2026 | Команда "ЯСНОПОНЯТНО" | Проект #10**

- **Дмитрий Горбунов** ([@grbn_dima](https://t.me/grbn_dima)) — тимлид, продукт, UX/UI
- **Анастасия Гапеева** — UX/UI, фронтенд
- **Иван Александров** — разработка, бизнес-логика
- **Claude Opus 4.5** — AI-ассистент команды

**Автор идеи:** Дмитрий Ботов ([@dmbotov](https://t.me/dmbotov)) — организатор Demo Day, AI Talent Hub

---

## Лицензия

MIT License — свободное использование для некоммерческих и коммерческих целей.

---

## Контакты

- **Live Demo:** https://team12.camp.aitalenthub.ru
- **Telegram Bot:** [@demoday_ai_talent_hub_test_bot](https://t.me/demoday_ai_talent_hub_test_bot)
- **GitHub:** [AI-Talent-Camp-2026/demoday-ai](https://github.com/AI-Talent-Camp-2026/demoday-ai)
- **Связаться:** [@grbn_dima](https://t.me/grbn_dima)

Разработано в рамках магистратуры «Искусственный интеллект» ИТМО
[AI Talent Hub](https://ai.itmo.ru) × [ИТМО](https://itmo.ru)
