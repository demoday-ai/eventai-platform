# EventAI

[![CI](https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/ci.yml)
[![CD](https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml/badge.svg)](https://github.com/AI-Talent-Camp-2026/demoday-ai/actions/workflows/cd.yml)

**Telegram-бот для персонализации мероприятий с параллельными треками**

На Demo Day 330 проектов в 10 залах. Гость успевает посетить меньше 20%. EventAI за 2 минуты диалога понимает интересы и выдаёт персональный топ проектов с рейтингом релевантности.

[Попробовать бота](https://t.me/demoday_ai_talent_hub_test_bot) · [Live Demo](https://team12.camp.aitalenthub.ru) · [Документация](./docs)

![Event Management](https://images.unsplash.com/photo-1540575467063-178a50c2df87?q=80&w=2000&auto=format&fit=crop)

---

## Зачем это нужно

> "Это пипец! Если вы упростите этот ужас, я буду благодарна."
> — Инна, организатор Demo Day

Мы провели 5 интервью с организаторами, экспертами, гостями и бизнес-партнёрами. Везде одна боль: **слишком много контента, слишком мало времени**.

- Гости пропускают 80% интересного из-за параллельных секций
- Эксперты идут вслепую — нет контекста о проектах заранее
- Бизнес не находит релевантные проекты среди сотен
- Организаторы составляют расписание вручную за ночь до события

---

## Что умеет бот

**Для гостей и партнёров:**
- Профилирование через AI-диалог — 2 минуты вместо анкет
- Персональный топ-15 проектов с рейтингом релевантности
- Q&A-помощник — 3-5 вопросов к каждому проекту под ваш профиль
- Сравнение проектов — таблица отличий для быстрого выбора
- Контакт с авторами — запрос через бота с согласия

**Для организаторов (админ-панель):**
- AI-кластеризация проектов по тематическим залам
- Автоматическое распределение экспертов по тегам
- Генерация расписания без конфликтов
- Напоминания и уведомления о сдвигах

---

## Качество рекомендаций

Мы проверили систему на 10 реальных профилях и 330 проектах с экспертными оценками:

| Метрика | Значение | Что это значит |
|---------|----------|----------------|
| NDCG@15 | **0.82** | Релевантные проекты в топе списка |
| Precision@15 | **0.71** | 7 из 10 рекомендаций попадают в цель |
| Recall@15 | **0.78** | Находим 8 из 10 подходящих проектов |

Как работает: поиск по тегам → анализ текста профиля → AI-ранжирование (Claude/GPT) → топ-15.

---

## Быстрый старт

```bash
# Клонировать
git clone https://github.com/AI-Talent-Camp-2026/demoday-ai.git
cd demoday-ai

# Настроить окружение
cp backend/.env.example backend/.env
# Заполнить BOT_TOKEN и OPENROUTER_API_KEY

# Запустить
docker compose up -d --build

# Применить миграции
docker compose exec backend alembic upgrade head
```

Готово: frontend на `localhost:3000`, бот работает в polling-режиме.

---

## Стек

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, python-telegram-bot 21.x
**Frontend:** React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui
**AI:** OpenRouter API (Claude, GPT)
**Infra:** Docker Compose, Traefik, Yandex Cloud

---

## Структура

```
├── frontend/          # React-приложение (админ-панель + лендинг)
├── backend/           # FastAPI + Telegram bot
│   ├── app/api/       # REST endpoints (60+)
│   ├── app/bot/       # Telegram handlers
│   ├── app/services/  # Бизнес-логика (кластеризация, рекомендации)
│   └── app/models/    # SQLAlchemy модели (34 сущности)
├── docs/              # Документация и артефакты discovery
└── data/              # Тестовые данные и оценка качества
```

---

## Customer Discovery

5 интервью, 17 гипотез, 4 сегмента:

| Кто | Инсайт |
|-----|--------|
| Организатор | 80 студентов не попали в расписание за ночь до DD |
| Эксперт | Идёт вслепую, нужен контекст за 1-2 дня |
| Бизнес | Из 330 проектов уверен в 15-20, остальное — лотерея |
| Гость | Посетила 5 из 330, пропустила самый интересный |

Подробнее: [Lean Canvas](./docs/01-discovery/lean-canvas.md) · [RICE-матрица](./docs/01-discovery/rice-matrix.md) · [Транскрипты](./docs/01-discovery/)

---

## Команда

**AI Talent Camp 2026 · Проект #10 · Команда "ЯСНОПОНЯТНО"**

- **Дмитрий Горбунов** — тимлид, продукт · [@grbn_dima](https://t.me/grbn_dima)
- **Анастасия Гапеева** — UX/UI, фронтенд
- **Иван Александров** — разработка, бизнес-логика

Автор идеи: **Дмитрий Ботов** ([@dmbotov](https://t.me/dmbotov)) — организатор Demo Day, AI Talent Hub

---

## Ссылки

- [Попробовать бота](https://t.me/demoday_ai_talent_hub_test_bot)
- [Live Demo](https://team12.camp.aitalenthub.ru)
- [API Documentation](https://team12.camp.aitalenthub.ru/api/v1/docs)
- [Deployment Guide](./DEPLOY.md)

---

*Разработано в рамках магистратуры «Искусственный интеллект» ИТМО*
*[AI Talent Hub](https://ai.itmo.ru) × [ИТМО](https://itmo.ru)*

MIT License
