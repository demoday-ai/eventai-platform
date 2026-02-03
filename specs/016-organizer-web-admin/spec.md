# Specification: Organizer Web Admin (EPIC-016)

**Version:** 1.0
**Date:** 2026-02-03
**Status:** Draft
**Branch:** `frontend`
**Dependencies:** EPIC-003 (Confirmations), EPIC-006 (Coverage), EPIC-011 (Dashboard)

---

## Problem Statement

Организаторам Demo Day нужен веб-интерфейс для мониторинга мероприятия с ноутбука/планшета. Telegram-бот удобен для быстрых команд, но для полноценного обзора с таблицами, фильтрами и детализацией нужен веб-дашборд.

**Ключевые боли:**
- В Telegram неудобно смотреть большие таблицы (покрытие залов, список проектов)
- Нет возможности держать дашборд открытым на втором экране
- Сложно быстро переключаться между разделами

---

## Scope

### MVP (к 6 февраля)

Минимальный веб-дашборд для организаторов с реал-тайм метриками.

### Out of Scope (после DD)

- Управление расписанием (drag-drop)
- Push-уведомления (WebSocket)
- Экспорт в Excel/PDF
- Графики и тренды
- Мобильное приложение

---

## User Stories

### US-001: Вход в админку (P0)

**Как организатор**, я хочу войти в веб-админку, чтобы видеть статус DD.

**Acceptance Criteria:**
- Форма входа с полем "Telegram ID" (временная заглушка)
- При вводе ID из списка `organizer_ids` — вход успешен
- При невалидном ID — сообщение об ошибке
- После входа — редирект на Dashboard

**Примечание:** Это временное решение. После настройки HTTPS — переход на Telegram Login Widget.

---

### US-002: Главный дашборд (P0)

**Как организатор**, я хочу видеть сводку по DD на одном экране.

**Acceptance Criteria:**
- Блок алертов (критические проблемы)
- Карточки метрик: студенты, эксперты, гости, залы
- Таблица покрытия залов
- Кнопка "Обновить" (ручной рефетч)
- Авто-обновление каждые 60 секунд

---

### US-003: Покрытие залов (P0)

**Как организатор**, я хочу видеть статус покрытия каждого зала экспертами.

**Acceptance Criteria:**
- Таблица: зал, кол-во проектов, эксперты (подтв./приглаш.), статус
- Цветовая индикация: зелёный (>=2), жёлтый (1), красный (0)
- Клик по залу — переход на детализацию

---

### US-004: Детализация зала (P1)

**Как организатор**, я хочу видеть детали конкретного зала.

**Acceptance Criteria:**
- Список экспертов: имя, статус приглашения, теги компетенций
- Список проектов: название, время, статус подтверждения, теги
- Непокрытые тематики (теги проектов без эксперта)
- Кнопка "Назад" на главный дашборд

---

### US-005: Список проектов (P1)

**Как организатор**, я хочу видеть все проекты с фильтрами.

**Acceptance Criteria:**
- Таблица: название, зал, время, статус, теги
- Фильтры: по залу, по статусу (подтверждён/неявка/ожидание)
- Поиск по названию
- Сортировка по времени/залу

---

### US-006: Неявки студентов (P1)

**Как организатор**, я хочу быстро найти неявившихся студентов.

**Acceptance Criteria:**
- Список студентов со статусом "не явился"
- Контактная информация (Telegram username)
- Фильтр по залу

---

## Functional Requirements

### FR-001: Авторизация (временная)

- Форма с полем "Telegram ID"
- Валидация: ID должен быть в списке `ORGANIZER_TELEGRAM_IDS`
- При успехе: сохранить токен в localStorage, редирект на `/dashboard`
- При ошибке: показать сообщение "Доступ запрещён"

### FR-002: Dashboard метрики

Отображать агрегированные данные:

| Метрика | Источник |
|---------|----------|
| Всего проектов | `GET /events/{id}/projects` count |
| Подтвердили | ParticipationRequest status=confirmed |
| Check-in | ParticipationRequest status=checked_in |
| Неявки | ParticipationRequest status=no_show |
| Эксперты приглашено | ExpertRoomAssignment count |
| Эксперты подтвердили | ExpertRoomAssignment status=accepted |
| Гости всего | User role=guest count |
| Гости по типам | User guest_subtype группировка |
| Залы покрыто | Rooms с >=2 accepted experts |

### FR-003: Алерты

Критические (красные):
- Зал с 0 подтверждённых экспертов
- Неявки >20% от подтвердивших студентов

Предупреждения (жёлтые):
- Зал с 1 подтверждённым экспертом
- Слоты в ближайший час без подтверждения

### FR-004: Покрытие залов

Таблица с колонками:
- Название зала
- Кол-во проектов
- Эксперты: `{accepted}/{total_assigned}`
- Статус: emoji + текст
- Действие: кнопка "Детали"

Статусы:
- `>=2 accepted` → 🟢 Покрыт
- `1 accepted` → 🟡 Частично
- `0 accepted` → 🔴 Не покрыт

### FR-005: Детализация зала

Секция "Эксперты":
- Имя (из User)
- Статус: proposed/accepted/rejected
- Теги компетенций (из ExpertTag)

Секция "Проекты":
- Название
- Время слота
- Статус подтверждения
- Теги проекта

Секция "Непокрытые тематики":
- Теги проектов, для которых нет эксперта с таким тегом

### FR-006: Auto-refresh

- Dashboard обновляется каждые 60 секунд
- Индикатор "Последнее обновление: HH:MM:SS"
- Кнопка ручного обновления

### FR-007: Responsive

- Desktop: полная таблица
- Tablet: адаптивные карточки
- Mobile: минимальный вид (только алерты и ключевые метрики)

---

## API Requirements

### Существующие endpoints (backend готов)

| Endpoint | Описание |
|----------|----------|
| `POST /api/v1/auth/login` | Авторизация |
| `GET /api/v1/auth/me` | Текущий пользователь |
| `GET /api/v1/events` | Список событий |
| `GET /api/v1/events/{id}` | Детали события |
| `GET /api/v1/projects` | Список проектов |
| `GET /api/v1/schedule/rooms` | Залы с проектами |
| `GET /api/v1/experts/assignments` | Назначения экспертов |

### Новые/доработанные endpoints (если потребуется)

| Endpoint | Описание | Приоритет |
|----------|----------|-----------|
| `GET /api/v1/admin/dashboard` | Агрегированные метрики для дашборда | P0 |
| `GET /api/v1/admin/coverage` | Покрытие залов с детализацией | P0 |
| `GET /api/v1/admin/rooms/{id}` | Детали зала (эксперты + проекты) | P1 |
| `GET /api/v1/admin/alerts` | Список активных алертов | P1 |

**Примечание:** Точный список доработок определится при интеграции. Возможно, всё уже есть или агрегируется на фронте.

---

## Technical Stack

| Компонент | Технология | Обоснование |
|-----------|------------|-------------|
| Framework | React 18 + Vite | Быстрый старт, HMR, простой билд |
| UI | shadcn/ui + Tailwind CSS | Качественные компоненты, кастомизация |
| State | TanStack Query (React Query) | Кеширование, авто-рефетч, девтулзы |
| Router | React Router v6 | Стандарт для SPA |
| HTTP | fetch + custom wrapper | Нет лишних зависимостей |
| Auth | JWT в localStorage | Простая интеграция |
| Build | Vite → static files | Деплой как статика |

---

## Project Structure

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/
│   │   ├── client.ts          # HTTP client с auth
│   │   ├── auth.ts            # Auth endpoints
│   │   ├── events.ts          # Events endpoints
│   │   ├── projects.ts        # Projects endpoints
│   │   ├── coverage.ts        # Coverage endpoints
│   │   └── types.ts           # API types
│   ├── components/
│   │   ├── ui/                # shadcn components
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── dashboard/
│   │   │   ├── AlertsCard.tsx
│   │   │   ├── MetricsCard.tsx
│   │   │   ├── CoverageTable.tsx
│   │   │   └── LastUpdated.tsx
│   │   ├── rooms/
│   │   │   ├── RoomCard.tsx
│   │   │   ├── ExpertsList.tsx
│   │   │   └── ProjectsList.tsx
│   │   └── projects/
│   │       ├── ProjectsTable.tsx
│   │       └── ProjectFilters.tsx
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── RoomDetail.tsx
│   │   └── Projects.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useDashboard.ts
│   │   └── useCoverage.ts
│   ├── lib/
│   │   ├── utils.ts
│   │   └── constants.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── .env.example
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

---

## UI Design

### Цветовая схема (нейтральная)

```
Background:    #ffffff (light) / #0f172a (dark)
Surface:       #f8fafc (light) / #1e293b (dark)
Primary:       #3b82f6 (blue-500)
Success:       #22c55e (green-500)
Warning:       #f59e0b (amber-500)
Error:         #ef4444 (red-500)
Text:          #0f172a (light) / #f8fafc (dark)
Text Muted:    #64748b (slate-500)
Border:        #e2e8f0 (light) / #334155 (dark)
```

### Компоненты

**Header:**
- Логотип "Demo Day Admin"
- Название текущего события
- Кнопка "Выйти"

**Sidebar (desktop):**
- Dashboard
- Проекты
- (будущее: Расписание, Настройки)

**Карточка метрики:**
```
┌─────────────────┐
│ 📋 Студенты     │
│      33         │  ← большое число
│ 91% подтвердили │  ← подпись
└─────────────────┘
```

**Таблица покрытия:**
```
┌─────────┬──────────┬──────────┬────────┬─────────┐
│ Зал     │ Проектов │ Эксперты │ Статус │         │
├─────────┼──────────┼──────────┼────────┼─────────┤
│ NLP     │    12    │   3/3    │ 🟢     │ [→]     │
│ CV      │    10    │   2/2    │ 🟢     │ [→]     │
│ Agents  │     8    │   1/2    │ 🟡     │ [→]     │
│ FinTech │     6    │   0/2    │ 🔴     │ [→]     │
└─────────┴──────────┴──────────┴────────┴─────────┘
```

**Алерт:**
```
┌─────────────────────────────────────────┐
│ 🔴 Зал "FinTech" без экспертов          │
│    Назначено: 2, подтвердили: 0         │
└─────────────────────────────────────────┘
```

---

## Deployment

### Build

```bash
cd frontend
npm run build
# Output: frontend/dist/
```

### Deploy на VM

```bash
# Копировать билд в nginx static
scp -r frontend/dist/* user@vm:/var/www/admin/

# Nginx config
server {
    listen 80;
    server_name admin.team10.camp.aitalenthub.ru;

    root /var/www/admin;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Environment

```env
# frontend/.env
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_NAME=Demo Day Admin
```

```env
# frontend/.env.production
VITE_API_URL=/api/v1
VITE_APP_NAME=Demo Day Admin
```

---

## Implementation Phases

### Phase 0: Scaffold + Mock Auth (День 1, первая половина)

**Задачи:**
- [ ] Инициализация проекта (Vite + React + TS)
- [ ] Настройка Tailwind + shadcn/ui
- [ ] Базовый роутинг (Login, Dashboard)
- [ ] Mock форма авторизации (поле Telegram ID)
- [ ] Хардкод проверки ID (список в константах)
- [ ] Сохранение "токена" в localStorage
- [ ] Protected route wrapper

**Результат:** Можно "войти" с тестовым ID и увидеть пустой Dashboard.

---

### Phase 1: Dashboard + Metrics (День 1-2)

**Задачи:**
- [ ] Layout (Header + Sidebar + Content)
- [ ] API client с авторизацией
- [ ] Интеграция с `GET /events`
- [ ] Карточки метрик (заглушки → реальные данные)
- [ ] Компонент алертов
- [ ] Auto-refresh (60 сек)
- [ ] Индикатор последнего обновления

**Результат:** Dashboard показывает реальные метрики из API.

---

### Phase 2: Coverage Table (День 2-3)

**Задачи:**
- [ ] Таблица покрытия залов
- [ ] Цветовая индикация статусов
- [ ] Интеграция с coverage API
- [ ] Переход на детализацию зала

**Результат:** Организатор видит покрытие всех залов.

---

### Phase 3: Room Detail (День 3)

**Задачи:**
- [ ] Страница детализации зала
- [ ] Список экспертов со статусами
- [ ] Список проектов зала
- [ ] Непокрытые тематики
- [ ] Навигация назад

**Результат:** Drill-down в конкретный зал.

---

### Phase 4: Projects List (День 4)

**Задачи:**
- [ ] Таблица всех проектов
- [ ] Фильтры (зал, статус)
- [ ] Поиск по названию
- [ ] Highlight неявок

**Результат:** Полный список проектов с фильтрацией.

---

### Phase 5: Polish + Deploy (День 5)

**Задачи:**
- [ ] Responsive адаптация
- [ ] Тёмная тема (toggle)
- [ ] Error boundaries
- [ ] Loading states
- [ ] Настройка nginx
- [ ] Деплой на VM
- [ ] Smoke testing

**Результат:** Продакшен-готовый дашборд.

---

## Success Criteria

| Критерий | Метрика |
|----------|---------|
| Вход работает | Организатор входит по Telegram ID |
| Метрики отображаются | Все 4 блока показывают данные |
| Покрытие видно | Таблица залов с цветами |
| Детализация работает | Клик по залу → детали |
| Скорость | Dashboard загружается <3 сек |
| Стабильность | Нет JS ошибок в консоли |

---

## Risks & Mitigations

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| API не готов | Низкая | Mock data на фронте, параллельная доработка |
| Нет времени на polish | Средняя | P0 функции first, polish — если успеем |
| CORS проблемы | Средняя | Настроить backend CORS или nginx proxy |

---

## Open Questions

1. **Формат Telegram ID в mock auth** — числовой ID или username?
   → Решение: числовой ID (как в `organizer_telegram_ids`)

2. **Нужен ли check-in через веб?**
   → Решение: нет, только просмотр (check-in через бота)

3. **Доступ только организаторам или добавить readonly для экспертов?**
   → Решение: только организаторы (MVP)
