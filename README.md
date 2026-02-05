<p align="center">
  <img src="https://images.unsplash.com/photo-1540575467063-178a50c2df87?q=80&w=800&auto=format&fit=crop" alt="EventAI" width="600">
</p>

<h1 align="center">EventAI</h1>

<p align="center">
  <strong>AI-навигатор для мероприятий с параллельными треками</strong>
</p>

<p align="center">
  <a href="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml"><img src="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml"><img src="https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml/badge.svg" alt="CD"></a>
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=white" alt="React">
</p>

<p align="center">
  <a href="https://t.me/demoday_ai_talent_hub_test_bot">Попробовать бота</a> •
  <a href="https://team12.camp.aitalenthub.ru">Live Demo</a> •
  <a href="./docs">Документация</a>
</p>

---

На Demo Day 330 проектов в 10 параллельных залах. Гость физически успевает посетить **меньше 20%**. EventAI за 2 минуты диалога понимает интересы и выдаёт персональную программу.

## Как это работает

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

## Возможности

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

## Качество рекомендаций

Проверено на 10 реальных профилях × 330 проектов с экспертной разметкой:

| Метрика | Значение | |
|---------|----------|---|
| **NDCG@15** | 0.82 | Релевантные проекты в топе |
| **Precision@15** | 0.71 | 7 из 10 попадают в цель |
| **Recall@15** | 0.78 | Находим 8 из 10 подходящих |

## Быстрый старт

```bash
git clone https://github.com/AI-Talent-Camp-2026/demoday-ai.git
cd demoday-ai

cp backend/.env.example backend/.env
# Заполнить BOT_TOKEN и OPENROUTER_API_KEY

docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Frontend: `localhost:3000` · Bot: polling mode

## Стек

| | |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16 |
| **Frontend** | React 19, TypeScript, Vite, Tailwind, shadcn/ui |
| **AI** | OpenRouter API (Claude, GPT) |
| **Infra** | Docker, Traefik, Yandex Cloud |

## Customer Discovery

> "Это пипец! Если вы упростите этот ужас, я буду благодарна."
> — Инна, организатор Demo Day

5 интервью показали общую боль: **слишком много контента, слишком мало времени**.

| Сегмент | Инсайт |
|---------|--------|
| Организатор | 80 студентов не попали в расписание за ночь до DD |
| Эксперт | Идёт вслепую, нужен контекст за 1-2 дня |
| Бизнес | Из 330 проектов уверен в релевантности 15-20 |
| Гость | Посетила 5 из 330, пропустила самый интересный |

[Lean Canvas](./docs/01-discovery/lean-canvas.md) · [RICE-матрица](./docs/01-discovery/rice-matrix.md) · [Транскрипты интервью](./docs/01-discovery/)

## Команда

**AI Talent Camp 2026 · Проект #10 · "ЯСНОПОНЯТНО"**

| | |
|---|---|
| **Дмитрий Горбунов** | Тимлид, продукт · [@grbn_dima](https://t.me/grbn_dima) |
| **Анастасия Гапеева** | UX/UI, фронтенд |
| **Иван Александров** | Разработка, бизнес-логика |

Автор идеи: **Дмитрий Ботов** ([@dmbotov](https://t.me/dmbotov)) — организатор Demo Day

---

<p align="center">
  <a href="https://ai.itmo.ru">AI Talent Hub</a> ×
  <a href="https://itmo.ru">ИТМО</a>
  <br>
  <sub>MIT License</sub>
</p>
