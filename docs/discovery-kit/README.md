# Discovery Kit v1.1.7

Набор AI-агентов и скиллов для автоматизации discovery-фазы разработки. Превращает идею в набор документов, готовых для передачи разработчику.

**Философия:** Docs as Code — всё в Markdown, версионируется, модульно.

---

## Быстрый старт

### Минимальный путь от идеи до разработки

```
Brief → User Story Map → NFR → C4 Architecture → ER Diagram → Готово к разработке
```

### Рекомендуемый полный путь

```
1. Brief (11)                    → описание идеи и проблемы
2. User Story Map (12)           → карта пользовательских сценариев
3. User Journey Map (13)         → визуализация пути пользователя
4. NFR (21)                      → нефункциональные требования
5. Lean Canvas (31)              → бизнес-модель
6. Market Research (32)          → анализ конкурентов
7. Personas (33)                 → портреты пользователей
8. Persona Interview (34)        → валидация идеи через симуляцию
9. C4 Diagrams (42)              → архитектура системы
10. ER Diagram (45)              → модель данных
11. API Inventory (47)           → список endpoints
12. Sequence Diagrams (46)       → диаграммы взаимодействий
13. Information Architecture (51)→ структура интерфейса
14. Wireframes (52)              → схемы экранов
15. Artifact Validator (61)      → финальная проверка консистентности
```

---

## Как использовать

### Шаг 1: Начните с идеи

Скопируйте содержимое нужного агента в чат с AI (Claude, GPT-4, Gemini) и начните диалог. Агент проведёт вас через процесс сбора информации.

**Пример:**
```
Скопируйте содержимое файла:
01-agents/01-discovery-agents/10-business-analyst.md

Вставьте в чат и напишите:
"У меня есть идея для приложения по трекингу привычек. Помоги создать Brief."
```

### Шаг 2: Следуйте рекомендуемому порядку

Каждый агент использует набор скиллов. Порядок важен — каждый следующий артефакт строится на предыдущих.

### Шаг 3: Сохраняйте артефакты

Все сгенерированные документы сохраняйте в папку `50-project-docs/` вашего проекта:

```
50-project-docs/
├── 01-your-project/
│   ├── brief.md
│   ├── user-story-map.md
│   ├── nfr.md
│   ├── personas/
│   │   └── buyer.md
│   ├── c4-architecture.md
│   ├── er-diagram.md
│   └── api-inventory.md
```

### Шаг 4: Валидируйте перед передачей в разработку

Используйте `61-artifact-validator.md` для проверки консистентности всех артефактов.

---

## Агенты и их скиллы

### Business Analyst «Clarifier» (10)

**Миссия:** Трансформировать абстрактные идеи в ясные, формализованные постановки задач.

| Скилл | Назначение | Файл |
|-------|------------|------|
| Brief Writing | Сбор требований, написание брифа | `11-brief-writing.md` |
| User Story Mapping | Создание карты пользовательских историй | `12-user-story-mapping.md` |
| User Journey Map | Визуализация пути пользователя (Mermaid) | `13-user-journey-map.md` |

**Выходные артефакты:**
- `brief.md` — описание проекта, проблемы, ограничений
- `user-story-map.md` — User Stories с Acceptance Criteria
- `user-journey-map.md` — Mermaid Journey диаграмма

---

### System Analyst «NFR Specialist» (20)

**Миссия:** Перевести бизнес-желания в измеримые инженерные метрики.

| Скилл | Назначение | Файл |
|-------|------------|------|
| NFR Collection | Сбор нефункциональных требований | `21-nfr-collection.md` |

**Выходные артефакты:**
- `nfr.md` — Performance, Reliability, Security, Scalability и др.

---

### Idea Challenger «Адвокат дьявола» (30)

**Миссия:** Конструктивно челленджить идею, найти слабые места и пути их усиления.

| Скилл | Назначение | Файл |
|-------|------------|------|
| Lean Canvas | Формирование бизнес-модели | `31-lean-canvas.md` |
| Market Research | Глубокий анализ рынка и конкурентов | `32-market-research.md` |
| Persona Generation | Создание детальных персон | `33-persona-generation.md` |
| Persona Interview | Симуляция custdev-интервью | `34-persona-interview.md` |

**Рекомендуемый порядок:**
1. Lean Canvas → структурировать бизнес-модель
2. Market Research → проверить конкурентов
3. Persona Generation → детализировать клиента
4. Persona Interview → «обстукать» идею

**Выходные артефакты:**
- `lean-canvas.md` — одностраничная бизнес-модель
- `market-research.md` — анализ конкурентов и рынка
- `personas/*.md` — профили целевых пользователей
- `interview-reports/*.md` — отчёты по интервью

---

### Solution Architect «Архитектор» (40)

**Миссия:** Трансформировать бизнес-требования в технические артефакты.

| Скилл | Назначение | Файл |
|-------|------------|------|
| Artifact Recommendation | Определение нужных артефактов | `41-artifact-recommendation.md` |
| C4 Diagrams | C4 Context + Container (Mermaid) | `42-c4-diagrams.md` |
| Tech Research | Deep Research технологий | `43-tech-research.md` |
| ADR | Architecture Decision Records | `44-adr.md` |
| ER Diagram | Модель данных + Data Dictionary | `45-er-diagram.md` |
| Sequence Diagrams | Диаграммы взаимодействий | `46-sequence-diagrams.md` |
| API Inventory | Список API endpoints | `47-api-inventory.md` |

**Выходные артефакты:**
- `artifact-recommendations.md` — какие артефакты нужны
- `c4-architecture.md` — архитектурная диаграмма
- `tech-research.md` — отчёт об исследовании технологий
- `adr/*.md` — Architecture Decision Records
- `er-diagram.md` — модель данных
- `sequence-diagrams.md` — диаграммы взаимодействий
- `api-inventory.md` — список endpoints

---

### Product Designer «Структуратор» (50)

**Миссия:** Превращать хаос требований в понятную структуру интерфейса.

| Скилл | Назначение | Файл |
|-------|------------|------|
| Information Architecture | Проектирование IA | `51-information-architecture.md` |
| Wireframe Spec | Unicode wireframes | `52-wireframe-spec.md` |

**Выходные артефакты:**
- `information-architecture.md` — sitemap, навигация
- `screens/*.md` — описания экранов с wireframes
- `user-flows.md` — схемы переходов

---

### Standalone скиллы

| Скилл | Назначение | Файл |
|-------|------------|------|
| Artifact Validator | Валидация консистентности артефактов | `61-artifact-validator.md` |

---

## Ключевые паттерны

### Clarification Loop

Все скиллы используют итеративный сбор требований с отслеживанием неопределённости:
- **Критические разделы** (70% веса) — без них решение невозможно
- **Вспомогательные** (30% веса) — улучшают качество
- **Цель:** неопределённость ≤ 0.02

### Escape Hatch

Всегда есть выход:
- «Не знаю» → разбить на части или предложить варианты
- «Хватит вопросов» → зафиксировать как открытый вопрос и продолжить

### Gold / Silver / Bronze

Для NFR и технических решений предлагаются варианты с разным уровнем амбиций:
- **Gold** — максимум (дорого, но надёжно)
- **Silver** — стандарт отрасли
- **Bronze** — минимум для старта

---

## Структура проекта

```
discovery-kit/
├── README.md                      # Этот файл
├── CLAUDE.md                      # Инструкции для Claude Code
├── 99-ideal-development-process.md # Полный pipeline (справочник)
│
├── 01-agents/
│   ├── 00-mother-of-all-agents.md # Lyra — метаагент
│   ├── 01-discovery-agents/
│   │   ├── 10-business-analyst.md
│   │   ├── 20-system-analyst.md
│   │   └── 30-idea-challenger.md
│   └── 02-solution-design-agents/
│       ├── 40-solution-architect.md
│       └── 50-product-designer.md
│
├── 02-skills/
│   ├── 01-discovery-skills/
│   │   ├── 11-brief-writing.md
│   │   ├── 12-user-story-mapping.md
│   │   ├── 13-user-journey-map.md
│   │   ├── 21-nfr-collection.md
│   │   ├── 31-lean-canvas.md
│   │   ├── 32-market-research.md
│   │   ├── 33-persona-generation.md
│   │   └── 34-persona-interview.md
│   └── 02-solution-design-skills/
│       ├── 41-artifact-recommendation.md
│       ├── 42-c4-diagrams.md
│       ├── 43-tech-research.md
│       ├── 44-adr.md
│       ├── 45-er-diagram.md
│       ├── 46-sequence-diagrams.md
│       ├── 47-api-inventory.md
│       ├── 51-information-architecture.md
│       ├── 52-wireframe-spec.md
│       └── 61-artifact-validator.md
│
├── 50-project-docs/               # Ваши проекты
│   └── 01-your-project/
│
└── 98-adapters/
    └── 99-education-adapter.md    # Адаптер для обучения
```

---

## Naming Convention

```
Первая цифра = номер агента (шаг 10)
Вторая цифра = номер скилла этого агента

10 — Business Analyst   → скиллы 11, 12, 13
20 — System Analyst     → скилл 21
30 — Idea Challenger    → скиллы 31, 32, 33, 34
40 — Solution Architect → скиллы 41-47
50 — Product Designer   → скиллы 51, 52
61 — Artifact Validator (standalone)
```

---

## Дополнительные материалы

### Lyra — Mother of All Agents

Файл `01-agents/00-mother-of-all-agents.md` содержит мета-агента Lyra для создания и оптимизации промптов. Используйте, если хотите создать собственного агента или улучшить существующий.

### Ideal Development Process

Файл `99-ideal-development-process.md` описывает полный цикл разработки от идеи до продакшена. Используйте как справочник для понимания, где Discovery Kit вписывается в общий процесс.

### Education Adapter

Файл `98-adapters/99-education-adapter.md` — шаблон для создания образовательных заметок. Добавьте его к любому скиллу, чтобы AI объяснял каждый шаг для обучения.

---