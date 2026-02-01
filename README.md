# AI-агент-куратор DemoDay

**AI Talent Camp 2026 | Команда "ЯСНОПОНЯТНО" | Проект #10**

AI-платформа для автоматизации подготовки и проведения Demo Day: кластеризация проектов, распределение экспертов, подтверждение участия, напоминания, обратная связь. Единая точка входа для всех ролей в Telegram.

## Проблема

На Demo Day ~330 проектов в 6-10 параллельных залах. Расписание составляется вручную одним человеком + ChatGPT (кластеризует плохо, дубликаты). 80 студентов не попали в расписание за ночь до DD. Нужно 60-80 экспертов, активных ~30-40. Обратная связь не доходит до студентов. Demo-Hero -- "фигня".

> "Целевая аудитория демодня -- это не гости, это студенты, эксперты." -- организатор

## Сегменты

| Сегмент | Кол-во | Приоритет |
|---------|--------|-----------|
| Организаторы | ~5 | Основной |
| Студенты | ~330 проектов | Основной |
| Эксперты / менторы | ~50 | Основной |
| Внешние гости | ~50 реальных | Вторичный |

## Структура репозитория

```
├── docs/
│   ├── 00-research/                    # Исследования и аналитика прошлого DD
│   │   ├── demoday-analytics.md        #   Масштаб, конфликты, сценарии, гипотезы
│   │   ├── past-demoday-projects.md    #   Каталог ~330 проектов по залам
│   │   └── demo-hero-example.md        #   Лог Demo-Hero + анализ UX-проблем
│   │
│   ├── 01-discovery/                   # Воркшоп 1: AI-First Customer Discovery
│   │   ├── customer-discovery.md       #   Опросник CustDev (орги + эксперты)
│   │   ├── interview-transcript.md     #   Транскрипт интервью с организатором
│   │   ├── lean-canvas.md              #   Lean Canvas (пивот по итогам CustDev)
│   │   ├── rice-matrix.md              #   RICE-матрица: 13 гипотез
│   │   ├── customer-journeys.md        #   AS-IS → TO-BE по 4 ролям
│   │   ├── icp.md                      #   Ideal Customer Profile
│   │   ├── pain-map.md                 #   Карта болей: 10 болей по сегментам
│   │   ├── jtbd.md                     #   Jobs-To-Be-Done: 9 jobs
│   │   └── vpc.md                      #   Value Proposition Canvas
│   │
│   └── 02-specification/               # Воркшоп 2: Specification-Driven Development
│       ├── 01-brief.md                 #   ✅ Бриф проекта
│       ├── 02-user-story-map.md        #   User Story Map
│       ├── 03-user-journey-map.md      #   User Journey Map (Mermaid)
│       ├── 04-nfr.md                   #   Нефункциональные требования
│       ├── 07-c4-architecture.md       #   C4-диаграмма архитектуры
│       ├── 08-er-diagram.md            #   ER-диаграмма + Data Dictionary
│       ├── 09-sequence-diagrams.md     #   Sequence-диаграммы
│       ├── 10-api-inventory.md         #   API-эндпоинты
│       ├── 11-validation-report.md     #   Кросс-валидация артефактов
│       ├── personas/                   #   Персоны пользователей
│       └── wireframes/                 #   Вайрфреймы экранов бота
│
├── telegram-log/                       # Telegram-бот для логирования чата
│   ├── bot.py                          #   Бот (python-telegram-bot, polling)
│   ├── send.py                         #   Отправка / удаление сообщений
│   ├── chat_config.json                #   ID чата
│   └── requirements.txt                #   Зависимости
│
├── CLAUDE.md                           # Контекст для Claude Code
└── README.md
```

## Команда

- **Дмитрий Горбунов** (@grbn_dima) -- тимлид, продукт, UX/UI
- **Анастасия Гапеева** -- UX/UI, фронтенд
- **Иван Александров** -- разработка, бизнес-логика
- **Claude** -- AI-ассистент команды
