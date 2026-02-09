# Идеальный процесс разработки: От идеи до работающего продукта

> [!CAUTION]
> ## Это справочный материал, НЕ инструкция для Discovery Kit
>
> Этот документ описывает **идеальный теоретический процесс** разработки от идеи до продакшена.
> Discovery Kit построен по **своей кастомной методологии**, которая отличается от описанного здесь.
>
> **Для работы с Discovery Kit используй:**
> - `README.md` — быстрый старт и описание агентов/скиллов
> - `CLAUDE.md` — инструкции для AI-ассистента
>
> **Этот файл — для чтения ради интереса**, чтобы понять общий контекст разработки ПО.

---

> Справочное руководство по организации полного цикла разработки программного продукта с использованием AI-ассистентов.

---

## Философия подхода

Прежде чем описывать процесс, важно понять базовые принципы:

1. **Документы — это не цель, а средство синхронизации.** Каждый артефакт существует, чтобы кто-то (человек или AI) мог принять решение или выполнить работу.

2. **Процесс не линейный.** Это граф с обратными связями. Архитектор может вернуть Brief на доработку. Tech Lead может сказать, что NFR нереалистичны.

3. **Человек нужен там, где нужно принятие решений с ответственностью.** AI может предложить, но подписаться под решением должен человек.

4. **Чем раньше ошибка — тем дешевле исправить.** Поэтому Discovery-фаза такая длинная и важная.

---

## Полный процесс

### PHASE 0: INCEPTION (Зарождение)

**Входит:** Сырая идея, боль, наблюдение

**Роль: Idea Validator / Challenger**

Задача — проверить идею ДО того, как начнём тратить ресурсы.

| Активность | Что делает |
|------------|-----------|
| **Idea Challenge** | Задаёт неудобные вопросы: "А кому это нужно?", "А почему сейчас?", "А что если уже есть?" |
| **Market Research** | Ищет конкурентов, аналоги, провалы в этой нише |
| **Assumption Mapping** | Выявляет ключевые допущения, которые нужно проверить |

**Выход:**
- Go / No-Go решение
- Список критических допущений для проверки
- Карта конкурентов и аналогов

**Нужен человек?** ДА — финальное решение "делаем / не делаем"

---

### PHASE 1: DISCOVERY (Исследование)

**Входит:** Валидированная идея

#### 1.1 Problem Space (Пространство проблемы)

**Роль: Business Analyst**

| Активность | Что делает |
|------------|-----------|
| **Brief Writing** | Фиксирует ЧТО и ЗАЧЕМ — проблема, контекст, constraints |
| **User Story Mapping** | Фиксирует КТО и КАК пользуется — роли, journey, stories |
| **Persona Creation** | Создаёт детальные портреты пользователей |
| **Journey Mapping** | Рисует полный путь пользователя (включая до и после продукта) |

**Что такое Persona Creation:**
Это не просто "менеджер Вася". Это детальный портрет:
- Демография, контекст работы
- Цели, страхи, мотивации
- Текущие инструменты и привычки
- Критерии успеха
- Цитаты (реальные или гипотетические)

**Что такое Journey Mapping:**
Это расширенный USM, который включает:
- Что происходит ДО взаимодействия с продуктом
- Эмоциональное состояние на каждом этапе
- Точки боли и восторга
- Что происходит ПОСЛЕ (follow-up, retention)

#### 1.2 Constraint Space (Пространство ограничений)

**Роль: System Analyst**

| Активность | Что делает |
|------------|-----------|
| **NFR Collection** | Собирает атрибуты качества (performance, security, scalability) |
| **Compliance Check** | Проверяет регуляторные требования детально |
| **Integration Inventory** | Инвентаризация внешних систем для интеграции |

**Что такое Compliance Check:**
Для каждого применимого регулирования (152-ФЗ, GDPR, PCI DSS):
- Конкретные требования, которые влияют на архитектуру
- Чек-лист того, что нужно реализовать
- Риски и штрафы за несоблюдение

**Что такое Integration Inventory:**
Для каждой внешней системы:
- Тип интеграции (API, файлы, БД)
- SLA внешней системы
- Формат данных
- Аутентификация
- Ограничения (rate limits, downtime windows)

---

### PHASE 2: SOLUTION DESIGN (Проектирование решения)

**Входит:** Brief, USM, NFR, Personas, Integrations

Это самая важная фаза, где принимаются ключевые решения.

#### 2.1 Product Design (Продуктовый дизайн)

**Роль: Product Designer**

| Активность | Что делает | Нужен человек? |
|------------|-----------|----------------|
| **Information Architecture** | Структура контента, навигация, sitemap | Частично — AI предлагает, человек валидирует |
| **Wireframe Spec** | Описание экранов в текстовом виде | AI может, человек проверяет |
| **Interaction Design** | Описание взаимодействий, состояний, переходов | AI может описать |
| **Visual Design** | Стиль, цвета, типографика | ДА — нужен дизайнер + Figma |

**Особенность Product Design:**
AI не может рисовать в Figma. Но AI может:
- Сгенерировать Information Architecture
- Описать каждый экран текстом (какие элементы, где расположены)
- Описать состояния и переходы
- Сгенерировать спецификацию для дизайнера

**Решение:**
Генерируется **Wireframe Spec** — текстовый документ, который дизайнер (человек) превращает в визуальный wireframe. Или использует для генерации через AI-инструменты типа Galileo AI, Uizard.

**Формат Wireframe Spec:**
```markdown
## Экран: Регистрация

### Layout
- Header: логотип слева, ссылка "Войти" справа
- Main: форма по центру, ширина 400px
- Footer: ссылки на документы

### Элементы формы (сверху вниз)
1. Заголовок "Создать аккаунт"
2. Input: Email (placeholder: "email@example.com")
3. Input: Пароль (type: password, показать/скрыть)
4. Checkbox: "Согласен с условиями" + ссылка
5. Button: "Зарегистрироваться" (primary, full-width)
6. Divider: "или"
7. Button: "Войти через Google" (secondary)

### Состояния
- Loading: кнопка disabled, спиннер
- Error: красная обводка поля, текст ошибки под полем
- Success: редирект на /onboarding
```

#### 2.2 Technical Architecture (Техническая архитектура)

**Роль: Solution Architect**

| Активность | Что делает | Выход |
|------------|-----------|-------|
| **C4 Context** | Система в контексте окружения | C4 Context Diagram (Mermaid) |
| **C4 Container** | Разбиение на развёртываемые единицы | C4 Container Diagram |
| **C4 Component** | Внутренняя структура ключевых контейнеров | C4 Component Diagram |
| **Tech Selection** | Выбор технологий с обоснованием | ADR (Architecture Decision Records) |
| **Deployment Design** | Как это будет развёрнуто | Deployment Diagram, IaC spec |

**Важно про C4:**
- **Context** — всегда нужен, показывает границы системы
- **Container** — всегда нужен, показывает из чего состоит
- **Component** — нужен для сложных контейнеров
- **Code** — обычно не рисуют, это уже код

**ADR (Architecture Decision Record):**
```markdown
# ADR-001: Выбор базы данных

## Контекст
Нужно хранить пользователей, их профили и историю действий.
NFR требует: 99.9% availability, < 50ms read latency.

## Рассмотренные варианты
1. PostgreSQL — реляционная, ACID, зрелая
2. MongoDB — документная, гибкая схема
3. CockroachDB — распределённая SQL

## Решение
PostgreSQL

## Обоснование
- Команда имеет опыт (Constraint из Brief)
- Данные структурированы, связи важны
- Managed решения доступны во всех облаках
- 99.9% достижимо с репликацией

## Последствия
- Нужен connection pooling для высокой нагрузки
- Миграции схемы требуют планирования
```

#### 2.3 Data Architecture (Архитектура данных)

**Роль: Data Architect**

| Активность | Что делает | Выход |
|------------|-----------|-------|
| **Domain Modeling** | Выделение сущностей из USM и Brief | Domain Model (концептуальный) |
| **ER Diagram** | Логическая модель данных | ER Diagram (Mermaid) |
| **Data Dictionary** | Описание каждого атрибута | Data Dictionary |
| **Data Flow** | Как данные движутся по системе | Data Flow Diagram |

**Domain Modeling vs ER Diagram:**
- **Domain Model** — концептуальный, на языке бизнеса (Пользователь, Заказ, Товар)
- **ER Diagram** — логический, ближе к реализации (users, orders, products, order_items)

**Data Dictionary пример:**
```markdown
## Таблица: users

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| id | UUID | NO | gen_random_uuid() | PK |
| email | VARCHAR(255) | NO | - | Уникальный, индекс |
| password_hash | VARCHAR(255) | NO | - | bcrypt hash |
| created_at | TIMESTAMP | NO | NOW() | Дата регистрации |
| deleted_at | TIMESTAMP | YES | NULL | Soft delete |

### Бизнес-правила
- Email должен быть уникальным
- При удалении — soft delete (deleted_at)
- password_hash никогда не возвращается в API
```

#### 2.4 API Design (Проектирование API)

**Роль: API Designer** (или часть Solution Architect)

| Активность | Что делает | Выход |
|------------|-----------|-------|
| **API Inventory** | Список всех нужных endpoints из USM | API Inventory |
| **API Contract** | Детальная спецификация каждого endpoint | OpenAPI 3.0 Spec |
| **API Examples** | Примеры запросов/ответов | Postman Collection / Examples |

**API Inventory:**
```markdown
## Auth
- POST /auth/register — регистрация
- POST /auth/login — вход
- POST /auth/logout — выход
- POST /auth/refresh — обновление токена

## Users
- GET /users/me — текущий пользователь
- PATCH /users/me — обновление профиля
- DELETE /users/me — удаление аккаунта

## Orders
- GET /orders — список заказов пользователя
- POST /orders — создание заказа
- GET /orders/{id} — детали заказа
- POST /orders/{id}/cancel — отмена
```

---

### PHASE 3: VALIDATION (Валидация)

**Входит:** Все артефакты Phase 2

Критическая фаза, которую часто пропускают. Цель — найти проблемы ДО написания кода.

**Роль: Technical Validator**

| Активность | Что делает | Нужен человек? |
|------------|-----------|----------------|
| **Architecture Review** | Проверка архитектуры на соответствие NFR | Желательно — Senior Architect |
| **Threat Modeling** | STRIDE анализ безопасности | ДА — Security специалист |
| **Cost Estimation** | Оценка стоимости инфраструктуры | Частично |
| **Technical Spike** | План проверки рискованных решений | ДА — разработчик делает spike |

**Threat Modeling (STRIDE):**
Для каждого компонента системы:
- **S**poofing — может ли кто-то притвориться другим?
- **T**ampering — может ли кто-то изменить данные?
- **R**epudiation — может ли кто-то отрицать действие?
- **I**nformation Disclosure — может ли утечь информация?
- **D**enial of Service — можно ли положить систему?
- **E**levation of Privilege — можно ли получить чужие права?

**Technical Spike:**
Если есть рискованное решение (новая технология, сложная интеграция):
1. Определить что проверяем
2. Timeboxed эксперимент (1-3 дня)
3. Go / No-Go / Pivot решение

---

### PHASE 4: PLANNING (Планирование разработки)

**Входит:** Валидированные артефакты

**Роль: Tech Lead**

| Активность | Что делает | Выход |
|------------|-----------|-------|
| **Epic Breakdown** | Разбиение USM на Epics | Epic list с acceptance criteria |
| **Technical Stories** | Разбиение на технические задачи | Technical Stories + Enabler Stories |
| **Dependency Mapping** | Определение зависимостей между задачами | Dependency Graph |
| **Estimation** | Оценка сложности | Story Points / T-shirt sizes |
| **Sprint Planning** | Формирование первого спринта | Sprint Backlog |

**Technical Story vs User Story:**
```markdown
## User Story (из USM)
[US-001][Покупатель] Как покупатель, я хочу зарегистрироваться,
чтобы сохранять историю заказов.

## Technical Stories (разбиение)
[TS-001] Создать таблицу users в PostgreSQL
[TS-002] Реализовать endpoint POST /auth/register
[TS-003] Добавить валидацию email (формат + уникальность)
[TS-004] Реализовать отправку confirmation email
[TS-005] Создать UI форму регистрации
[TS-006] Интегрировать форму с API
[TS-007] Написать E2E тест регистрации
```

**Enabler Stories:**
```markdown
[EN-001] Настроить CI/CD pipeline
[EN-002] Настроить мониторинг и алерты
[EN-003] Создать базовую структуру проекта
[EN-004] Настроить линтеры и форматтеры
```

---

### PHASE 5: DEVELOPMENT (Разработка)

**Входит:** Sprint Backlog, все спецификации

Здесь AI может помогать, но человек остаётся ключевым.

**Роль: Code Assistant**

| Активность | Что делает | Нужен человек? |
|------------|-----------|----------------|
| **Code Generation** | Генерация кода по спецификации | ДА — review обязателен |
| **Test Generation** | Генерация тестов | ДА — проверка покрытия |
| **Code Review** | Автоматический review PR | Частично — финальное решение за человеком |
| **Documentation** | Генерация документации из кода | Частично |

**Важно:** Код генерируется не из воздуха, а из:
- Technical Story (что делать)
- API Contract (какой интерфейс)
- Data Dictionary (какие данные)
- ADR (какие технологии и почему)

---

### PHASE 6: QUALITY ASSURANCE (Проверка качества)

**Входит:** Написанный код

**Роль: QA Engineer** (частично автоматизируется)

| Активность | Что делает | Нужен человек? |
|------------|-----------|----------------|
| **Test Case Generation** | Генерация тест-кейсов из USM | Частично |
| **Test Execution** | Запуск автотестов | Нет |
| **Exploratory Testing** | Исследовательское тестирование | ДА — человек лучше находит edge cases |
| **Performance Testing** | Проверка соответствия NFR | Частично |

---

### PHASE 7: DEPLOYMENT & OPERATIONS (Развёртывание и эксплуатация)

**Роль: DevOps / SRE**

| Активность | Что делает |
|------------|-----------|
| **Deployment Checklist** | Чек-лист перед релизом |
| **Runbook Generation** | Инструкции по эксплуатации |
| **Incident Response** | Playbook для инцидентов |

---

## Визуализация полного процесса

```
PHASE 0: INCEPTION
┌─────────────────────────────────────────────────────────────────┐
│  [Сырая идея] → [Idea Validator] → [Go/No-Go] → [Assumptions]   │
│                        ↑                                         │
│                   [Человек: решение]                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 1: DISCOVERY
┌─────────────────────────────────────────────────────────────────┐
│  [Business Analyst]        [System Analyst]                     │
│  ├─ Brief                  ├─ NFR                               │
│  ├─ USM                    ├─ Compliance Check                  │
│  ├─ Personas               └─ Integration Inventory             │
│  └─ Journey Map                                                 │
│                        ↑                                         │
│                   [Человек: валидация понимания]                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 2: SOLUTION DESIGN
┌─────────────────────────────────────────────────────────────────┐
│  [Product Designer]        [Solution Architect]                 │
│  ├─ IA                     ├─ C4 Context                        │
│  ├─ Wireframe Spec         ├─ C4 Container                      │
│  └─ Interaction Design     ├─ Tech Selection (ADR)              │
│        ↓                   └─ Deployment Design                 │
│  [Человек-дизайнер]                                             │
│  └─ Visual Design (Figma)  [Data Architect]                     │
│                            ├─ Domain Model                      │
│  [API Designer]            ├─ ER Diagram                        │
│  ├─ API Inventory          ├─ Data Dictionary                   │
│  └─ API Contract           └─ Data Flow                         │
│                        ↑                                         │
│                   [Человек: архитектурные решения]              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 3: VALIDATION
┌─────────────────────────────────────────────────────────────────┐
│  [Technical Validator]                                          │
│  ├─ Architecture Review ← [Человек: Senior Architect]           │
│  ├─ Threat Modeling ← [Человек: Security]                       │
│  ├─ Cost Estimation                                             │
│  └─ Technical Spike ← [Человек: разработчик]                    │
│                        ↓                                         │
│              [Go / No-Go / Pivot]                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 4: PLANNING
┌─────────────────────────────────────────────────────────────────┐
│  [Tech Lead]                                                    │
│  ├─ Epic Breakdown                                              │
│  ├─ Technical Stories                                           │
│  ├─ Dependency Mapping                                          │
│  ├─ Estimation ← [Человек: команда оценивает]                   │
│  └─ Sprint Planning                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
PHASE 5-7: BUILD → TEST → DEPLOY
┌─────────────────────────────────────────────────────────────────┐
│  [Development] → [QA] → [Deployment]                            │
│       ↑            ↑          ↑                                 │
│  [Человек]    [Человек]  [Человек]                              │
│  Code Review   Exploratory  Release Decision                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                         [Production]
                              ↓
                    [Feedback → Phase 0/1]
```

---

## Где ОБЯЗАТЕЛЬНО нужен человек

| Этап | Почему человек |
|------|----------------|
| **Go/No-Go решения** | Ответственность за бизнес-решение |
| **Visual Design** | Креативность + инструменты (Figma) |
| **Architecture Review** | Опыт, интуиция, ответственность |
| **Security Review** | Критичность, ответственность |
| **Technical Spikes** | Руки на клавиатуре, эксперименты |
| **Code Review** | Финальное качество, ответственность |
| **Exploratory Testing** | Человек лучше находит неожиданное |
| **Release Decision** | Ответственность за production |

---

## Где AI может работать автономно

| Этап | Что делает AI |
|------|---------------|
| **Brief Writing** | Ведёт интервью, структурирует |
| **USM Creation** | Генерирует stories из brief |
| **NFR Collection** | Предлагает метрики, ищет стандарты |
| **ER Diagram** | Генерирует из domain knowledge |
| **API Contract** | Генерирует OpenAPI из USM |
| **Technical Stories** | Разбивает US на задачи |
| **Code Generation** | Генерирует по спецификации |
| **Test Generation** | Генерирует тесты |
| **Documentation** | Генерирует из кода |

---

## Обратные связи (Feedback Loops)

Процесс не линейный. Важные обратные связи:

```
Architecture Review → может вернуть на NFR (нереалистичные требования)
                    → может вернуть на Brief (scope слишком большой)

Threat Modeling → может добавить NFR (новые security requirements)
               → может изменить Architecture (новые компоненты)

Cost Estimation → может вернуть на Tech Selection (слишком дорого)
               → может вернуть на NFR (снизить требования)

Development → может вернуть на API Contract (невозможно реализовать)
           → может вернуть на Architecture (непредвиденная сложность)

QA → может вернуть на USM (неполные acceptance criteria)
   → может добавить Technical Stories (баги)

Production Feedback → новый цикл (улучшения, новые фичи)
```

---

## Формат артефактов

Все артефакты должны быть:
1. **Текстовые** — Markdown, чтобы версионировать в Git
2. **Машиночитаемые** — где возможно (OpenAPI, Mermaid)
3. **Связанные** — ссылки между документами
4. **Версионируемые** — история изменений

**Рекомендуемая структура output:**
```
output/
├── 00-idea/
│   ├── assumptions.md
│   └── competitors.md
├── 01-discovery/
│   ├── brief.md
│   ├── usm.md
│   ├── personas/
│   │   ├── buyer.md
│   │   └── seller.md
│   └── nfr.md
├── 02-design/
│   ├── architecture/
│   │   ├── c4-context.md (with Mermaid)
│   │   ├── c4-container.md
│   │   └── adr/
│   │       ├── 001-database.md
│   │       └── 002-auth.md
│   ├── data/
│   │   ├── domain-model.md
│   │   ├── er-diagram.md
│   │   └── data-dictionary.md
│   ├── api/
│   │   └── openapi.yaml
│   └── ui/
│       └── wireframe-specs/
│           ├── registration.md
│           └── dashboard.md
├── 03-validation/
│   ├── architecture-review.md
│   ├── threat-model.md
│   └── cost-estimate.md
└── 04-planning/
    ├── epics.md
    ├── technical-stories.md
    └── sprint-1.md
```

---

## APPENDIX A: UI/Design Pipeline — "Structure First, Visual Later"

Это дополнение к основному процессу, которое решает проблему: **как не застревать в Pixel Perfect на этапе Discovery, но потом легко перейти к красивому UI?**

### Проблема

Типичная ловушка:
1. Хочется сделать красиво → садимся в Figma → рисуем недели
2. Гипотеза не проверена → переделываем всё
3. Или: делаем "на коленке" → потом невозможно переделать без полного рефакторинга

### Решение: Lean UX + Design Tokens

**Принцип:** Разделяем **контракт компонента** (что он делает, какие состояния) и **скин** (как выглядит).

```
[Структура/UX] ← фиксируем сразу, меняем редко
[Визуал/UI]    ← меняем легко через токены
```

### Что такое Design Tokens

Design tokens — это переменные для всех визуальных решений:

| Категория | Примеры токенов |
|-----------|-----------------|
| **Цвета** | `--color-surface`, `--color-primary`, `--color-text-muted` |
| **Отступы** | `--space-1`, `--space-2`, `--space-4` (4px, 8px, 16px) |
| **Радиусы** | `--radius-sm`, `--radius-card`, `--radius-full` |
| **Тени** | `--shadow-sm`, `--shadow-card`, `--shadow-modal` |
| **Типографика** | `--font-size-body`, `--font-weight-bold`, `--line-height-tight` |

**Ключевое правило:** В коде используем **семантические токены**, а не конкретные значения.

```jsx
// ПЛОХО — привязка к конкретным значениям
<div className="bg-[#0F172A] rounded-[14px] p-[18px]">

// ХОРОШО — семантические токены
<div className="bg-surface rounded-card p-space-4">
```

### UI Pipeline по этапам

#### Этап 0: Инициализация токенов (до первого экрана)

**Когда:** Сразу после Tech Selection, до начала разработки UI.

**Что делаем:**
1. Создаём минимальный набор токенов (10-15 штук)
2. Подключаем их к Tailwind/CSS
3. Документируем в Storybook

**Минимальный набор токенов для старта:**

```css
/* tokens.css */
:root {
  /* Цвета — нейтральные для MVP */
  --color-surface: #ffffff;
  --color-surface-elevated: #f8fafc;
  --color-border: #e2e8f0;
  --color-text: #1e293b;
  --color-text-muted: #64748b;
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-error: #ef4444;
  --color-success: #22c55e;

  /* Отступы — 4px шкала */
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2rem;     /* 32px */

  /* Радиусы */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-full: 9999px;

  /* Тени */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
}
```

**Tailwind config:**

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        surface: 'var(--color-surface)',
        'surface-elevated': 'var(--color-surface-elevated)',
        border: 'var(--color-border)',
        // ...
      },
      spacing: {
        'space-1': 'var(--space-1)',
        'space-2': 'var(--space-2)',
        // ...
      },
      borderRadius: {
        'card': 'var(--radius-md)',
        'button': 'var(--radius-sm)',
        // ...
      }
    }
  }
}
```

#### Этап 1: MVP/Discovery — строим на токенах

**Когда:** Вся разработка UI.

**Правила для разработчика:**

```markdown
## UI Development Rules

### 1. Только семантические токены
Используй: `bg-surface`, `text-foreground`, `border-default`, `rounded-card`, `gap-space-3`
Не используй: hex-цвета, px-значения в классах

### 2. Никаких произвольных значений
Если значения нет в токенах — это сигнал добавить новый токен, а не хардкодить.
Исключения помечай комментарием: `{/* WHY: одноразовое значение для X */}`

### 3. Компонент = Контракт + Скин
- Props/состояния/семантика — фиксированы
- Стили — только через токены
- Варианты: size (sm/md/lg), intent (primary/secondary/danger), state (default/hover/disabled)

### 4. Все состояния сразу
Каждый интерактивный элемент должен иметь:
- default, hover, focus, active, disabled
- loading (если применимо)
- error (если применимо)
```

**Что получаем на выходе:**
- Работающий UI с правильной структурой
- Все состояния и взаимодействия
- Выглядит "нейтрально", но функционально
- Готов к редизайну

#### Этап 2: Visual Polish — меняем токены

**Когда:** После валидации гипотезы, когда понятно что оставляем.

**Что делаем:**
1. Дизайнер создаёт визуальный язык в Figma
2. Экспортируем токены из Figma (Tokens Studio)
3. Трансформируем в код (Style Dictionary)
4. Подключаем новые токены
5. Точечно правим композицию где нужно

**Пример трансформации:**

```css
/* До (MVP) */
:root {
  --color-primary: #3b82f6;        /* generic blue */
  --radius-card: 0.5rem;           /* 8px */
  --shadow-card: 0 4px 6px rgba(0,0,0,0.1);
}

/* После (Brand) */
:root {
  --color-primary: #7c3aed;        /* brand purple */
  --radius-card: 1rem;             /* 16px — более мягкий */
  --shadow-card: 0 8px 30px rgba(124,58,237,0.15); /* цветная тень */
}
```

**Результат:** UI меняется без изменения кода компонентов.

### Инструменты для pipeline

| Инструмент | Для чего |
|------------|----------|
| **Figma + Tokens Studio** | Дизайн токенов, экспорт в JSON |
| **Style Dictionary** | Трансформация JSON → CSS/JS/Tailwind |
| **Storybook** | Изолированная разработка компонентов |
| **Chromatic** | Visual regression testing (до/после) |

### Pipeline автоматизации токенов

```
[Figma Tokens] → [JSON export] → [Style Dictionary] → [CSS Variables]
                                                            ↓
                                                    [Tailwind Config]
                                                            ↓
                                                    [Components]
```

**Команда для CI:**
```bash
# Генерация токенов из JSON
npx style-dictionary build --config style-dictionary.config.js
```

### Защита от регрессий

Когда меняешь токены — как убедиться, что ничего не сломалось?

**Storybook + Chromatic:**
1. Каждый компонент имеет stories со всеми состояниями
2. Chromatic делает скриншоты до/после
3. Видно что изменилось намеренно vs случайно

```jsx
// Button.stories.tsx
export const Primary = () => <Button intent="primary">Click me</Button>
export const Secondary = () => <Button intent="secondary">Click me</Button>
export const Disabled = () => <Button disabled>Click me</Button>
export const Loading = () => <Button loading>Click me</Button>
```

### Интеграция в основной Pipeline

```
PHASE 2: SOLUTION DESIGN
├── 2.1 Product Design
│   ├── Information Architecture
│   ├── Wireframe Spec (текстовый)
│   └── Interaction Design
│
├── 2.1.1 UI Foundation
│   ├── Design Tokens Definition
│   ├── Component Contract Spec
│   └── Storybook Setup
│
├── 2.2 Technical Architecture
...

PHASE 5: DEVELOPMENT
├── 5.1 Backend Development
├── 5.2 Frontend Development (на токенах)
...

PHASE 8: VISUAL POLISH (после валидации гипотезы)
├── 8.1 Visual Design (Figma)
├── 8.2 Token Update
├── 8.3 Composition Tweaks
└── 8.4 Visual Regression Check
```

### Промпт для Frontend-разработчика

```markdown
# UI Development Protocol

## Принцип
Строим UI "семантикой", а не "пикселями". Визуал меняется через токены, структура остаётся.

## Обязательные правила

1. **Только токены**
   - Цвета: `bg-surface`, `text-primary`, `border-default`
   - Отступы: `p-space-4`, `gap-space-2`, `m-space-6`
   - Радиусы: `rounded-card`, `rounded-button`
   - Тени: `shadow-card`, `shadow-modal`

2. **Никаких magic numbers**
   - НЕ делай: `p-[18px]`, `bg-[#1a1a1a]`, `rounded-[14px]`
   - Если значения нет — предложи добавить токен

3. **Все состояния сразу**
   - Интерактивные элементы: default, hover, focus, active, disabled
   - Асинхронные: loading, error, success, empty

4. **Компонент = Props + Variants**
   - Props: данные и callbacks
   - Variants: size (sm/md/lg), intent (primary/secondary/danger)
   - Стили: только через токены и variants

5. **Исключения документируй**
   - Если нужно отступить от токенов — комментарий WHY
   - `{/* WHY: специфичный отступ для выравнивания с иконкой */}`

## Структура компонента

interface ButtonProps {
  children: React.ReactNode
  intent?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  onClick?: () => void
}

// Стили через токены
const variants = {
  intent: {
    primary: 'bg-primary text-primary-foreground hover:bg-primary-hover',
    secondary: 'bg-surface border border-default hover:bg-surface-elevated',
    danger: 'bg-error text-error-foreground hover:bg-error-hover',
  },
  size: {
    sm: 'px-space-2 py-space-1 text-sm',
    md: 'px-space-4 py-space-2 text-base',
    lg: 'px-space-6 py-space-3 text-lg',
  }
}
```

### Когда этот подход НЕ работает

1. **Меняется композиция, не только стили**
   - Карточка товара: была вертикальная → стала горизонтальная
   - Решение: минимизируй такие изменения, или планируй их заранее

2. **Сложные анимации и микровзаимодействия**
   - Токены не покрывают motion design
   - Решение: добавь motion tokens или делай это отдельным слоем

3. **A/B тесты визуала**
   - Нужны разные "скины" одновременно
   - Решение: CSS-in-JS с theme provider или CSS layers

### Резюме подхода

| Этап | Что делаем | Кто делает | Результат |
|------|-----------|------------|-----------|
| **Discovery** | Wireframe Spec + IA | AI | Структура понятна |
| **UI Foundation** | Токены + Storybook | AI + Human review | База для разработки |
| **Development** | Компоненты на токенах | AI | Работающий UI |
| **Validation** | Тестируем гипотезу | Human | Go/No-Go |
| **Visual Polish** | Figma → Tokens → Code | Human designer + AI | Красивый UI |

**Главный инсайт:** Pixel Perfect откладывается не потому что он не важен, а потому что сначала нужно убедиться, что мы строим правильную вещь. А когда убедились — редизайн через токены занимает часы, а не недели.

---

## Заключение

Идеальный процесс разработки — это не водопад и не хаос. Это **структурированная гибкость**:

1. **Фазы существуют** — чтобы ничего не забыть
2. **Обратные связи работают** — чтобы исправлять ошибки рано
3. **Человек включается там, где нужна ответственность** — не везде
4. **AI ускоряет рутину** — генерация, структурирование, поиск
5. **Артефакты связаны** — каждый документ ссылается на источник

Минимальный путь от идеи до кода:

```
Brief → USM → NFR → C4 Container → ER Diagram → Technical Stories → [Код]
```

Это даёт всё необходимое для начала разработки. Остальные артефакты добавляются по мере роста сложности проекта и команды.
