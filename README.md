<p align="center">
  <a href="https://ai.itmo.ru"><strong>AI Talent Hub</strong></a> ×
  <a href="https://itmo.ru"><strong>ИТМО</strong></a>
  <br>
  <sub>AI Talent Camp 2026 · Проект #12</sub>
</p>

<p align="center">
  <img src="https://images.unsplash.com/photo-1540575467063-178a50c2df87?q=80&w=800&auto=format&fit=crop" alt="EventAI" width="600">
</p>

<h1 align="center">EventAI</h1>

<p align="center">
  <strong>AI-платформа для организаторов конференций</strong><br>
  <sub>Бот + админка для Demo Day, конференций, хакатонов</sub>
</p>

<p align="center">
  <a href="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml"><img src="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml"><img src="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml/badge.svg" alt="CD"></a>
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=white" alt="React">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-proprietary-red" alt="License"></a>
</p>

<p align="center">
  <a href="https://t.me/demoday_ai_talent_hub_test_bot">Попробовать бота</a> •
  <a href="https://team12.camp.aitalenthub.ru">Live Demo</a> •
  <a href="./docs">Документация</a>
</p>

<br>

Сотни проектов в параллельных залах. Гости видят менее 20%. EventAI профилирует интересы через AI-диалог и составляет персональный топ проектов с рейтингом релевантности.

<br>

## Возможности

**Для гостей и партнёров** — персональный топ проектов, Q&A-помощник с вопросами под профиль, сравнение проектов, контакт с авторами через бота.

**Для организаторов** — AI-кластеризация проектов по залам, автораспределение экспертов, генерация расписания, напоминания.

<br>

## Пример диалога

```
Гость:  HR-директор, ищу AI в найме

Бот:    Нашёл 8 проектов. Топ-3:

        1. AI Interview Copilot — 94%
           Зал 2 · HR, Agents

        2. PD-Audit — 87%
           Зал 5 · NLP, HR

        3. ExamLab — 82%
           Зал 3 · EdTech
```

<br>

## Качество рекомендаций

Оценка на 10 профилях × 330 проектов с экспертной разметкой:

| Метрика | Значение | Описание |
|:--------|:--------:|:---------|
| NDCG@15 | 0.82 | Релевантные проекты в топе |
| Precision@15 | 0.71 | 7 из 10 попадают в цель |
| Recall@15 | 0.78 | Находим 8 из 10 подходящих |

Пайплайн: TF-IDF по тегам → LLM re-ranking (Claude/GPT) → топ-15

<br>

## Быстрый старт

```bash
git clone https://github.com/AI-Talent-Camp-2026/demoday-ai.git && cd demoday-ai
cp backend/.env.example backend/.env  # заполнить BOT_TOKEN, OPENROUTER_API_KEY
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Frontend `localhost:3000` · API docs `localhost:8000/api/v1/docs`

<br>

## Архитектура

```
frontend/          React 19, TypeScript, Vite, Tailwind, shadcn/ui
backend/
├── app/api/       REST API, 60+ endpoints
├── app/bot/       Telegram handlers
├── app/services/  profiling, clustering, matching, qa
└── app/models/    34 SQLAlchemy модели
```

<br>

## Стек

**Backend** — Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, APScheduler, python-telegram-bot 21.x

**Frontend** — React 19, TypeScript, Vite, TanStack Query, Tailwind, shadcn/ui

**AI** — OpenRouter (Claude, GPT), TF-IDF + LLM re-ranking

**Infra** — Docker Compose, Celery, RabbitMQ, Redis, Traefik, Yandex Cloud

<br>

## Мониторинг

| Сервис | URL | Описание |
|:-------|:----|:---------|
| Admin Panel | [team12.camp.aitalenthub.ru](https://team12.camp.aitalenthub.ru) | Панель организатора |
| RabbitMQ | [/rabbitmq/](https://team12.camp.aitalenthub.ru/rabbitmq/) | Очередь задач |
| Flower | [/flower/](https://team12.camp.aitalenthub.ru/flower/) | Мониторинг Celery воркеров |
| API Docs | [/docs](https://team12.camp.aitalenthub.ru/docs) | Swagger UI |

Логин/пароль для RabbitMQ и Flower: `demoday` / `demoday`

<br>

## Customer Discovery

> "Это пипец! Если вы упростите этот ужас, я буду благодарна." — организатор Demo Day

4 интервью, одна боль: слишком много контента, слишком мало времени. Гости пропускают 80% интересного, эксперты идут вслепую, организаторы делают расписание за ночь до события.

[Lean Canvas](./docs/01-discovery/lean-canvas.md) · [RICE-матрица](./docs/01-discovery/rice-matrix.md) · [Интервью](./docs/01-discovery/)

<br>

## Команда

**"ЯСНОПОНЯТНО"** — AI Talent Camp 2026, проект #12

- **Дмитрий Горбунов** — тимлид, продукт · [@grbn_dima](https://t.me/grbn_dima)
- **Анастасия Гапеева** — UX/UI, фронтенд · [@agapeeva](https://t.me/agapeeva)
- **Иван Александров** — разработка · [@ivanich_spb](https://t.me/ivanich_spb)

Автор идеи: **Дмитрий Ботов** [@dmbotov](https://t.me/dmbotov)

<br>

## Лицензия

Проприетарная. Любое использование требует коммерческой лицензии.

Контакт: [@grbn_dima](https://t.me/grbn_dima)
