<p align="center">
  <a href="https://ai.itmo.ru"><strong>AI Talent Hub</strong></a> ×
  <a href="https://itmo.ru"><strong>ИТМО</strong></a>
  <br>
  <sub>AI Talent Camp 2026 · Проект #10</sub>
</p>

<p align="center">
  <img src="https://images.unsplash.com/photo-1540575467063-178a50c2df87?q=80&w=800&auto=format&fit=crop" alt="EventAI" width="600">
</p>

<h1 align="center">EventAI</h1>

<p align="center">
  <strong>Персональная программа каждому гостю за 2 минуты</strong>
</p>

<p align="center">
  <a href="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml"><img src="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml"><img src="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml/badge.svg" alt="CD"></a>
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/license-proprietary-red" alt="License">
</p>

<p align="center">
  <a href="https://t.me/demoday_ai_talent_hub_test_bot">Попробовать бота</a> •
  <a href="https://team12.camp.aitalenthub.ru">Live Demo</a> •
  <a href="./docs">Документация</a>
</p>

---

## Для организаторов конференций и Demo Day

Сотни проектов в параллельных залах. Гости видят **менее 20%**. Telegram-бот профилирует интересы и составляет персональный топ.

**330** проектов · **10** залов · **2 мин** на профиль

---

## Проблема

> "Это пипец! Если вы упростите этот ужас, я буду благодарна."
> — Инна, организатор Demo Day

Чем больше проектов — тем меньше видят гости:
- Гости не знают, куда идти
- Бизнес-партнёры не находят нужные проекты
- Эксперты перегружены
- Организаторы составляют расписание вручную за ночь до события

---

## Решение

Telegram-бот делает мероприятие персональным.

**Для гостей и партнёров**
- Персональный топ проектов с рейтингом релевантности
- Q&A-помощник — вопросы к проекту под ваш профиль
- Сравнение проектов — таблица отличий
- Контакт с авторами — через бота с согласия

**Для организаторов**
- AI-кластеризация проектов по залам
- Автораспределение экспертов по тегам
- Генерация расписания без конфликтов
- Напоминания и уведомления

---

## Как это выглядит

```
Гость: Интересуюсь NLP и рекомендательными системами,
       ищу проекты для потенциального найма в команду

  Бот: Нашёл 12 проектов по вашему профилю. Топ-3:

       1. AI Recruiter Assistant (94% релевантности)
          Зал 2 · NLP, Agents

       2. Resume Screening Engine (87%)
          Зал 5 · NLP, HR

       3. Interview Copilot (82%)
          Зал 2 · LLM, Agents

       Показать Q&A вопросы к проектам?
```

---

## Качество рекомендаций

Проверено на 10 реальных профилях × 330 проектов с экспертной разметкой:

| Метрика | Значение | Что это значит |
|---------|----------|----------------|
| NDCG@15 | 0.82 | Релевантные проекты в топе списка |
| Precision@15 | 0.71 | 7 из 10 рекомендаций попадают в цель |
| Recall@15 | 0.78 | Находим 8 из 10 подходящих проектов |

**Пайплайн:** поиск по тегам → TF-IDF скоринг → LLM re-ranking (Claude/GPT) → топ-15

---

## Архитектура

```
├── frontend/           React 19, TypeScript, Vite, Tailwind, shadcn/ui
│   └── src/pages/      32 страницы (Landing, Dashboard, Clustering...)
│
├── backend/            Python 3.12, FastAPI, SQLAlchemy 2.0
│   ├── app/api/        REST API (60+ endpoints)
│   ├── app/bot/        Telegram handlers (python-telegram-bot 21.x)
│   ├── app/services/   Бизнес-логика (кластеризация, рекомендации, Q&A)
│   └── app/models/     34 SQLAlchemy модели
│
├── data/eval/          Оценка качества рекомендаций
└── docs/               Спецификация, CustDev артефакты
```

**Ключевые сервисы:**
- `profiling_service.py` — AI-профилирование через диалог
- `clustering_service.py` — LLM-кластеризация проектов по залам
- `matching_service.py` — подбор экспертов по тегам
- `qa_service.py` — генерация Q&A вопросов

---

## API

```
POST /api/v1/leads              Форма заявки с лендинга
POST /api/v1/profile            Создание/обновление профиля гостя
POST /api/v1/recommendations    Генерация рекомендаций
GET  /api/v1/projects           Список проектов
POST /api/v1/clustering/run     Запуск AI-кластеризации
GET  /api/v1/admin/dashboard    Метрики для организатора
```

Полная документация: `/api/v1/docs` (Swagger)

---

## Быстрый старт

```bash
git clone https://github.com/AI-Talent-Camp-2026/demoday-ai.git
cd demoday-ai

cp backend/.env.example backend/.env
# Заполнить BOT_TOKEN и OPENROUTER_API_KEY

docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Frontend: `localhost:3000` · Bot: polling mode · API: `localhost:8000/api/v1/docs`

---

## Стек

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 16, Alembic, APScheduler

**Frontend:** React 19, TypeScript, Vite, TanStack Query, Tailwind CSS, shadcn/ui

**AI:** OpenRouter API (Claude Sonnet, GPT-4), TF-IDF + LLM re-ranking

**Infra:** Docker Compose, Traefik (SSL), Yandex Cloud VM

---

## Customer Discovery

5 интервью показали общую боль: **слишком много контента, слишком мало времени**.

| Сегмент | Инсайт |
|---------|--------|
| Организатор | 80 студентов не попали в расписание за ночь до DD |
| Эксперт | Идёт вслепую, нужен контекст за 1-2 дня |
| Бизнес | Из 330 проектов уверен в релевантности 15-20 |
| Гость | Посетила 5 из 330, пропустила самый интересный |

[Lean Canvas](./docs/01-discovery/lean-canvas.md) · [RICE-матрица](./docs/01-discovery/rice-matrix.md) · [Транскрипты](./docs/01-discovery/)

---

## Команда

**AI Talent Camp 2026 · Проект #10 · "ЯСНОПОНЯТНО"**

- **Дмитрий Горбунов** — тимлид, продукт · [@grbn_dima](https://t.me/grbn_dima)
- **Анастасия Гапеева** — UX/UI, фронтенд
- **Иван Александров** — разработка, бизнес-логика

Автор идеи: **Дмитрий Ботов** ([@dmbotov](https://t.me/dmbotov)) — организатор Demo Day

---

## Лицензия

Все права защищены. Использование, копирование, модификация и распространение без письменного разрешения авторов запрещено.

Для коммерческого использования: [@grbn_dima](https://t.me/grbn_dima)
