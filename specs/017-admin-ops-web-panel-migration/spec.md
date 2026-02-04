# Specification: Admin Ops Migration (Telegram -> Web Admin)

**Version:** 1.0
**Date:** 2026-02-04
**Status:** Draft
**Target branch:** `frontend` (UI) + `main` (backend API gaps)
**Dependencies:** EPIC-016 (Web Admin Dashboard, реализован)

---

## 1) Goal

Перенести **все** администраторские операции из Telegram-бота в web админ-панель, чтобы организатор мог полностью управлять DD из браузера. Максимально переиспользуем уже реализованные backend API endpoints и закрываем gaps для операций, которых пока нет в web-потоке.

---

## 2) Scope

### 2.1 Операционные workflow (основные — из Telegram-бота)

| # | Workflow | Telegram-команда | Приоритет |
|---|----------|-----------------|-----------|
| 1 | Кластеризация проектов по залам | `/clustering` | P0 |
| 2 | Матчинг экспертов по залам | `/experts` | P0 |
| 3 | Управление расписанием | `/schedule` | P0 |
| 4 | Загрузка проектов/выступающих | `/clustering` (upload step) | P0 |
| 5 | Загрузка экспертов (bulk) | `/experts` (upload step) | P0 |
| 6 | Рассылки и оповещения | `/broadcast`, `/reminders` | P1 |
| 7 | Брифинг экспертов | `/briefing` | P1 |
| 8 | Coverage мониторинг + gaps | `/coverage` | P1 |
| 9 | Участие студентов | `/broadcast`, `/status` | P1 |
| 10 | Эскалации экспертов | `/experts` (escalations) | P1 |

### 2.2 Управленческие функции (новые, не было в Telegram)

| # | Функция | Приоритет |
|---|---------|-----------|
| 11 | Настройка дат конференции | P1 |
| 12 | Управление организаторами (CRUD) | P2 |
| 13 | Единичное создание/редактирование эксперта | P2 |
| 14 | Bulk import гостей с subtype | P2 |
| 15 | Unified messaging с таргетингом аудитории | P2 |

---

## 3) Что уже реализовано (reuse baseline)

### 3.1 Web frontend (EPIC-016, реализован)

Read-only дашборд:
- Login по Telegram ID (mock auth)
- Dashboard: метрики студентов/экспертов/гостей/залов + алерты
- Coverage table с drill-down в детализацию зала
- Projects list с фильтрами (зал, статус, поиск)

Файлы: `frontend/src/pages/Dashboard.tsx`, `ProjectsList.tsx`, `RoomDetail.tsx`, `Login.tsx`

### 3.2 Backend API — операционные endpoints (все реализованы)

#### Кластеризация (`backend/app/api/projects.py`)
- `POST /api/v1/projects/upload` — загрузка проектов (CSV/JSON)
- `GET /api/v1/projects` — список проектов с фильтрами
- `POST /api/v1/clustering/run` — запуск LLM-кластеризации (num_rooms, feedback)
- `GET /api/v1/clustering/current` — текущий результат кластеризации
- `POST /api/v1/clustering/{run_id}/move` — перемещение проекта между залами
- `POST /api/v1/clustering/{run_id}/approve` — одобрение кластеризации

#### Эксперты и матчинг (`backend/app/api/experts.py`)
- `POST /api/v1/experts/upload` — загрузка экспертов (JSON)
- `GET /api/v1/experts` — список экспертов с фильтрами
- `GET /api/v1/experts/{expert_id}` — детали эксперта
- `POST /api/v1/matching/run` — запуск матчинга экспертов по залам
- `GET /api/v1/matching/current` — текущий результат матчинга
- `POST /api/v1/matching/{assignment_id}/move` — перемещение эксперта
- `POST /api/v1/matching/approve` — одобрение матчинга
- `GET /api/v1/invites/preview` — preview приглашений
- `POST /api/v1/invites/confirm` — отправка приглашений
- `GET /api/v1/coverage` — покрытие залов
- `GET /api/v1/coverage/gaps` — анализ пробелов
- `GET /api/v1/coverage/{room_id}` — детали покрытия зала
- `GET /api/v1/escalations` — список эскалаций
- `POST /api/v1/escalations/{id}/resolve` — закрытие эскалации

#### Расписание (`backend/app/api/schedule.py`)
- `POST /api/v1/schedule/generate` — генерация расписания из кластеризации
- `GET /api/v1/schedule` — просмотр расписания (фильтры: room_id, day, status)
- `POST /api/v1/schedule/approve` — одобрение расписания
- `PATCH /api/v1/schedule/slots/{slot_id}` — правка слота (время, зал, статус)
- `GET /api/v1/schedule/changes` — аудит-лог изменений

#### Рассылки и уведомления (`backend/app/api/participation.py`, `schedule.py`, `reminders.py`)
- `POST /api/v1/participation/broadcast` — рассылка расписания студентам
- `GET /api/v1/participation/summary` — статус подтверждений
- `GET /api/v1/participation/unacknowledged` — неподтвердившие
- `GET /api/v1/reminders/preview` — preview напоминаний
- `POST /api/v1/reminders/send` — ручная отправка
- `POST /api/v1/reminders/cancel` — отмена
- `GET /api/v1/reminders/batches` — история батчей
- `GET /api/v1/notifications/dashboard` — статус доставки
- `GET /api/v1/notifications` — лог уведомлений

#### Дашборд (`backend/app/api/admin.py`)
- `GET /api/v1/admin/dashboard` — агрегированные метрики
- `GET /api/v1/admin/coverage` — покрытие залов
- `GET /api/v1/admin/rooms/{room_id}` — детали зала
- `GET /api/v1/admin/projects` — проекты с фильтрами

### 3.3 Ограничения / Gaps

| Gap | Описание |
|-----|----------|
| Нет UI для кластеризации | API готов, нужен frontend |
| Нет UI для матчинга | API готов, нужен frontend |
| Нет UI для расписания | API готов, нужен frontend |
| Нет UI для upload | API готов, нужен frontend |
| Нет UI для рассылок | API готов, нужен frontend |
| Нет UI для брифинга | Сервис есть, нужен API endpoint + frontend |
| Нет CRUD организаторов | Сейчас через env `ORGANIZER_TELEGRAM_IDS`, нужен API + UI |
| Нет единичного создания эксперта | Только bulk upload, нужен API + UI |
| Нет редактирования дат события | Модель есть, нужен PATCH endpoint + UI |
| Нет bulk import гостей | Гости = users с role=guest и guest_subtype, нужен endpoint + UI |
| Нет unified messaging | Рассылки привязаны к конкретным аудиториям, нужен общий UI |

---

## 4) Mapping: полный workflow → текущая база → gap

### 4.1 Операционные workflow (API готов, нужен только UI)

| # | Workflow | Существующие endpoints | Frontend gap |
|---|----------|----------------------|--------------|
| 1 | Upload проектов | `POST /projects/upload` | Экран загрузки + summary ошибок/дубликатов |
| 2 | Кластеризация | `POST /clustering/run`, `GET /clustering/current`, `POST /clustering/{id}/move`, `POST /clustering/{id}/approve` | Wizard: параметры → результат → drag/move → approve |
| 3 | Upload экспертов | `POST /experts/upload` | Экран загрузки + summary |
| 4 | Матчинг экспертов | `POST /matching/run`, `GET /matching/current`, `POST /matching/{id}/move`, `POST /matching/approve` | Wizard: run → review по залам → move → approve |
| 5 | Приглашения | `GET /invites/preview`, `POST /invites/confirm` | Preview + кнопка Send |
| 6 | Генерация расписания | `POST /schedule/generate`, `GET /schedule`, `POST /schedule/approve` | Wizard: параметры → таблица → approve |
| 7 | Правка слотов | `PATCH /schedule/slots/{id}`, `GET /schedule/changes` | Inline edit в таблице расписания |
| 8 | Broadcast студентам | `POST /participation/broadcast`, `GET /participation/summary` | Кнопка Send + статус |
| 9 | Напоминания | `GET /reminders/preview`, `POST /reminders/send`, `POST /reminders/cancel` | Preview + Send/Cancel |
| 10 | Coverage gaps | `GET /coverage`, `GET /coverage/gaps`, `GET /coverage/{room_id}` | Уже частично есть в dashboard, добавить actions |
| 11 | Эскалации | `GET /escalations`, `POST /escalations/{id}/resolve` | Список + кнопка Resolve |

### 4.2 Управленческие функции (нужен API + UI)

| # | Функция | Что уже есть | Gap (backend) | Gap (frontend) |
|---|---------|--------------|---------------|----------------|
| 12 | Даты конференции | Модель `events` с `start_date/end_date` | `PATCH /admin/events/current` | Date picker + Save |
| 13 | CRUD организаторов | env var `ORGANIZER_TELEGRAM_IDS` | `GET/POST/DELETE /admin/organizers` + миграция авторизации | Список + Add/Remove |
| 14 | Единичное создание эксперта | Bulk upload only | `POST /admin/experts` (single create) | Форма: имя, telegram, теги |
| 15 | Bulk import гостей | Гости = `users` с `role=guest` + `guest_subtype` | `POST /admin/guests/upload` (создаёт users с preset subtype) | Upload + subtype selector |
| 16 | Unified messaging | Разные endpoints для разных аудиторий | `POST /admin/messages/preview` + `POST /admin/messages/send` с target audience filter | Template + audience + preview + send |

---

## 5) Target UX в web admin

### Навигация (sidebar)

```
Dashboard          ← уже реализовано (EPIC-016)
├─ Метрики
├─ Алерты
└─ Coverage table

Data Import        ← NEW
├─ Проекты (CSV/JSON)
├─ Эксперты (JSON)
└─ Гости (CSV/JSON)

Кластеризация      ← NEW (основной workflow)
├─ Параметры + Run
├─ Результат по залам
├─ Перемещение проектов
└─ Одобрение

Эксперты           ← NEW (основной workflow)
├─ Матчинг (Run → Review → Approve)
├─ Приглашения (Preview → Send)
├─ Coverage & Gaps
├─ Эскалации
├─ Брифинг (Preview → Send)
└─ Добавить эксперта

Расписание         ← NEW (основной workflow)
├─ Генерация
├─ Просмотр / Правка слотов
├─ Одобрение
└─ Лог изменений

Рассылки           ← NEW
├─ Broadcast студентам
├─ Напоминания (Preview → Send → Cancel)
├─ Unified messaging (аудитория + шаблон)
├─ Статус доставки
└─ История батчей

Участие            ← NEW
├─ Summary
└─ Неподтвердившие

Настройки          ← NEW
├─ Даты конференции
└─ Организаторы (Add/Remove)
```

---

## 6) API plan (reuse-first)

### 6.1 Используем без изменений (35+ endpoints)

Все endpoints из секции 3.2 — полностью переиспользуем в web UI.

### 6.2 Новые endpoints

#### A) Briefing (сервис есть, нет REST endpoint)
- `GET /api/v1/admin/briefing/preview` — preview: кол-во экспертов, пример карточки
  - Response: `{ total_experts, with_telegram, without_telegram, sample_card }`
- `POST /api/v1/admin/briefing/send` — массовая отправка карточек проектов
  - Response: `{ sent, failed, skipped, elapsed_ms }`

#### B) Conference dates
- `PATCH /api/v1/admin/events/current`
  - Input: `{ start_date?, end_date?, name?, description? }`
  - Response: updated event

#### C) Organizers management
- `GET /api/v1/admin/organizers` — список организаторов
  - Response: `[{ telegram_id, username?, name?, added_at }]`
- `POST /api/v1/admin/organizers` — добавить организатора
  - Input: `{ telegram_id, username?, name? }`
- `DELETE /api/v1/admin/organizers/{telegram_id}` — удалить организатора

**Стратегия миграции авторизации:**
1. Добавить таблицу `organizers` (telegram_id, username, name, added_at)
2. При старте приложения: seed из env `ORGANIZER_TELEGRAM_IDS` в таблицу (если пуста)
3. Обновить `config.py → is_organizer()`: проверять DB, fallback на env
4. Env var остаётся как bootstrap-механизм, DB — как primary source

#### D) Expert single create/edit
- `POST /api/v1/admin/experts` — создать эксперта
  - Input: `{ name, telegram_contact?, telegram_user_id?, position?, tags[] }`
  - Response: created expert
- `PATCH /api/v1/admin/experts/{expert_id}` — редактировать эксперта
  - Input: `{ name?, telegram_contact?, position?, tags[]? }`

#### E) Guest bulk import
- `POST /api/v1/admin/guests/upload`
  - Input: CSV/JSON file + `default_subtype` (investor | business_partner | mentor | hr | jury | other)
  - Создаёт `users` с `role=guest` и указанным `guest_subtype`
  - Response: `{ parsed, imported, duplicates, errors }`

**Примечание:** В DB нет отдельной сущности "partner". Бизнес-партнёры — это `users` с `role=guest` и `guest_subtype` (investor, business_partner, mentor, hr, jury). Upload создаёт пользователей с предзаполненным subtype.

#### F) Unified messaging
- `POST /api/v1/admin/messages/preview`
  - Input: `{ template, target_audience: { role?, guest_subtype?, room_id? }, include_links: bool }`
  - Response: `{ recipient_count, sample_message, recipients_preview[] }`
- `POST /api/v1/admin/messages/send`
  - Input: same as preview + `dry_run: bool`
  - Response: `{ sent, failed, skipped }`

**Примечание:** Объединяет функционал partner messaging, broadcast и ad-hoc рассылок в единый интерфейс с таргетингом по role/subtype/room.

---

## 7) Delivery plan (phases)

### Phase 1: Core Operations (MVP — организатор уходит из Telegram)

**Цель:** Полный цикл подготовки DD из веба.

**Frontend:**
- [ ] Data Import: upload projects (CSV/JSON) + upload experts (JSON) — UI поверх существующих endpoints
- [ ] Clustering wizard: параметры → run → просмотр результата по залам → move проектов → approve
- [ ] Expert matching wizard: run → review по залам → move экспертов → approve
- [ ] Invite flow: preview → send
- [ ] Schedule: generate → view таблица → approve

**Backend:** Нет новых endpoints — всё уже реализовано.

**Критерий выхода:** Организатор выполняет полный pipeline (upload → cluster → match → invite → schedule) без Telegram.

### Phase 2: Monitoring & Notifications

**Frontend:**
- [ ] Coverage gaps UI с drill-down (endpoints готовы)
- [ ] Escalations: список + resolve (endpoints готовы)
- [ ] Broadcast студентам: send + status (endpoints готовы)
- [ ] Reminders: preview + send + cancel + batch history (endpoints готовы)
- [ ] Participation summary + unacknowledged list (endpoints готовы)
- [ ] Notification dashboard: статус доставки (endpoint готов)
- [ ] Schedule slot editing: inline правка + change log (endpoints готовы)

**Backend:** Нет новых endpoints.

### Phase 3: Extended Management (API gaps)

Разбита на 5 подфаз (3a–3e). 3a/3b/3c — независимы, можно делать параллельно. 3d зависит от наличия экспертов (3b). 3e — последней (зависит от 3b, 3c).

```
3a (Settings)  →  3b (Expert CRUD)  →  3c (Guest import)  →  3d (Briefing)  →  3e (Messaging)
  минимальный       изолированный        reuse upload         reuse send         самый сложный
  warm-up           новый CRUD           паттерн              паттерн            зависит от 3b,3c
```

#### Phase 3a: Settings — Даты конференции

**Объём:** минимальный (warm-up)

**Backend:**
- [ ] Убедиться что модель `events` имеет `start_date`/`end_date`
- [ ] `PATCH /api/v1/admin/events/current` — обновление дат/названия/описания (6.2.B)

**Frontend:**
- [ ] Страница `Settings.tsx` с секцией "Даты конференции"
- [ ] Date picker (start/end), поля name/description
- [ ] Кнопка Save, success/error toast
- [ ] Добавить пункт "Настройки" в sidebar (иконка Settings)

**Критерий выхода:** Организатор меняет даты DD из UI, изменения отражаются в API.

#### Phase 3b: Expert single create/edit

**Объём:** средний, изолированный

**Backend:**
- [ ] `POST /api/v1/admin/experts` — создание эксперта (name, telegram_contact, telegram_user_id, position, tags[]) (6.2.D)
- [ ] `PATCH /api/v1/admin/experts/{expert_id}` — редактирование (6.2.D)

**Frontend:**
- [ ] Кнопка "Добавить эксперта" на странице ExpertMatching или в sidebar
- [ ] Модалка/страница с формой: имя, Telegram, позиция, теги (multi-select)
- [ ] Валидация обязательных полей
- [ ] Inline-редактирование эксперта из списка

**Критерий выхода:** Организатор создаёт/редактирует эксперта без bulk-файла.

#### Phase 3c: Guest bulk import

**Объём:** средний, переиспользует upload-паттерн из DataImport

**Backend:**
- [ ] `POST /api/v1/admin/guests/upload` — CSV/JSON + `default_subtype` (investor | business_partner | mentor | hr | jury | other) (6.2.E)
- [ ] Создаёт `users` с `role=guest` + `guest_subtype`
- [ ] Response: `{ parsed, imported, duplicates, errors }`

**Frontend:**
- [ ] Секция "Гости" на странице DataImport.tsx (reuse `FileUpload` + `ImportSummary`)
- [ ] Dropdown для выбора subtype перед загрузкой
- [ ] Summary с результатами

**Критерий выхода:** Организатор загружает CSV/JSON гостей с preset subtype, видит summary.

#### Phase 3d: Briefing экспертов

**Объём:** средний, Send-паттерн (preview → confirm → result)

**Backend:**
- [ ] `GET /api/v1/admin/briefing/preview` — total_experts, with_telegram, without_telegram, sample_card (6.2.A)
- [ ] `POST /api/v1/admin/briefing/send` — массовая отправка карточек проектов (6.2.A)
- [ ] Response: `{ sent, failed, skipped, elapsed_ms }`

**Frontend:**
- [ ] Страница `Briefing.tsx` или секция внутри Experts
- [ ] Preview: метрики (total, with_telegram, without_telegram) + пример карточки
- [ ] Кнопка Send с confirmation dialog
- [ ] Результат: sent/failed/skipped

**Критерий выхода:** Организатор видит preview, нажимает Send, видит sent/failed/skipped.

#### Phase 3e: Unified messaging

**Объём:** самый крупный, зависит от 3b и 3c (нужны данные о гостях, экспертах)

**Backend:**
- [ ] `POST /api/v1/admin/messages/preview` — template, target_audience (role, guest_subtype, room_id), include_links (6.2.F)
- [ ] `POST /api/v1/admin/messages/send` — то же + dry_run (6.2.F)
- [ ] Response preview: `{ recipient_count, sample_message, recipients_preview[] }`
- [ ] Response send: `{ sent, failed, skipped }`

**Frontend:**
- [ ] Страница `Messaging.tsx` (новая) или секция в Notifications
- [ ] Audience builder: role selector, guest_subtype filter, room filter
- [ ] Template textarea с placeholder-переменными
- [ ] Preview: количество получателей + пример сообщения + список
- [ ] Кнопка Send с dry_run toggle
- [ ] Результат: sent/failed/skipped

**Критерий выхода:** Организатор выбирает аудиторию, пишет шаблон, видит preview, отправляет.

### Phase 4: Access Management + Hardening

**Frontend + Backend:**
- [ ] Organizers CRUD — **нужен API + миграция авторизации** (6.2.C)
- [ ] Аудит-лог admin действий
- [ ] Retry/observability по отправкам
- [ ] Anti-duplication для импортов
- [ ] Telegram Login Widget (замена mock auth)

---

## 8) Acceptance criteria

### Phase 1

| # | Функция | Критерий |
|---|---------|----------|
| 1 | Upload проектов | Админ загружает CSV/JSON из UI, видит summary (loaded/errors/duplicates) |
| 2 | Upload экспертов | Админ загружает JSON из UI, видит summary |
| 3 | Кластеризация | Админ задаёт число залов, запускает, видит результат по залам, перемещает проекты, одобряет |
| 4 | Матчинг | Админ запускает matching, видит экспертов по залам, перемещает, одобряет |
| 5 | Приглашения | Админ видит preview (кол-во, пример сообщения), нажимает Send, видит результат |
| 6 | Расписание | Админ генерирует из кластеризации, видит таблицу слотов, одобряет |

### Phase 2

| # | Функция | Критерий |
|---|---------|----------|
| 7 | Coverage | Админ видит пробелы по залам, кандидатов для закрытия |
| 8 | Эскалации | Админ видит unresolved, может пометить resolved |
| 9 | Broadcast | Админ отправляет расписание студентам, видит статус подтверждений |
| 10 | Напоминания | Preview → Send/Cancel, видна история батчей |
| 11 | Slot editing | Админ меняет время/зал слота, видит лог изменений |

### Phase 3a: Settings

| # | Функция | Критерий |
|---|---------|----------|
| 12 | Даты DD | Даты редактируются из UI, сохраняются через PATCH, отражаются в API |

### Phase 3b: Expert CRUD

| # | Функция | Критерий |
|---|---------|----------|
| 13 | Создание эксперта | Форма: имя, telegram, позиция, теги → создаётся через POST |
| 14 | Редактирование эксперта | Inline-edit или модалка → обновляется через PATCH |

### Phase 3c: Guest import

| # | Функция | Критерий |
|---|---------|----------|
| 15 | Guests import | Загрузка CSV/JSON с preset subtype, summary (parsed/imported/duplicates/errors) |

### Phase 3d: Briefing

| # | Функция | Критерий |
|---|---------|----------|
| 16 | Брифинг | Preview (total, with/without telegram, sample) → Send → видно sent/failed/skipped |

### Phase 3e: Messaging

| # | Функция | Критерий |
|---|---------|----------|
| 17 | Unified messaging | Выбор аудитории (role/subtype/room), шаблон, preview (count + sample), send (с dry_run) |

### Phase 4

| # | Функция | Критерий |
|---|---------|----------|
| 18 | Организаторы | Add/Remove без правки env, fallback на env работает |
| 19 | Аудит-лог | Все admin actions логируются с timestamp и actor |

---

## 9) Risks

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Phase 1 затягивается из-за объёма UI | Средняя | Wizard-паттерн: минимальный UI, step-by-step |
| Рассинхрон env vs DB для организаторов | Средняя | Seed из env при старте, env как fallback |
| Сущность "guest" неоднозначна для import | Низкая | Использовать существующую модель users + role + subtype |
| Отправка через бота из web нестабильна | Средняя | Retry + статус доставки + уведомление об ошибках |
| Параллельные изменения из Telegram и Web | Средняя | Оптимистичная блокировка, warning при конфликте |

---

## 10) Non-goals (для этого этапа)

- Полная замена всех Telegram user-facing сценариев (гостевой чат, студенческий ack)
- Реалтайм push/WebSocket
- Drag-and-drop расписание
- BI-дашборды и advanced аналитика
- Мобильное приложение

---

## 11) Technical notes

### Структура frontend (расширение EPIC-016)

Новые pages и компоненты добавляются в существующий frontend проект:

```
frontend/src/
├── pages/
│   ├── Dashboard.tsx           ← существует
│   ├── ProjectsList.tsx        ← существует
│   ├── RoomDetail.tsx          ← существует
│   ├── Login.tsx               ← существует
│   ├── DataImport.tsx          ← NEW
│   ├── Clustering.tsx          ← NEW
│   ├── ExpertMatching.tsx      ← NEW
│   ├── Schedule.tsx            ← NEW
│   ├── Notifications.tsx       ← NEW
│   ├── Participation.tsx       ← NEW
│   ├── Escalations.tsx         ← NEW
│   └── Settings.tsx            ← NEW
├── components/
│   ├── clustering/             ← NEW
│   │   ├── ClusteringWizard.tsx
│   │   ├── RoomCard.tsx
│   │   └── MoveProjectDialog.tsx
│   ├── experts/                ← NEW
│   │   ├── MatchingWizard.tsx
│   │   ├── InvitePreview.tsx
│   │   └── MoveExpertDialog.tsx
│   ├── schedule/               ← NEW
│   │   ├── ScheduleTable.tsx
│   │   ├── SlotEditor.tsx
│   │   └── ChangeLog.tsx
│   ├── import/                 ← NEW
│   │   ├── FileUpload.tsx
│   │   └── ImportSummary.tsx
│   └── notifications/          ← NEW
│       ├── BroadcastPanel.tsx
│       ├── ReminderPanel.tsx
│       └── DeliveryStatus.tsx
└── lib/
    └── api-client.ts           ← расширить новыми вызовами
```

### Переиспользуемые UI-паттерны

- **Wizard pattern** (для clustering, matching, schedule): step indicator → action → review → approve
- **Upload pattern** (для projects, experts, guests): file input → validation → summary → confirm
- **Send pattern** (для invites, broadcast, reminders, briefing): preview → confirm → result

---

## 12) Следующий артефакт

После согласования → `tasks.md` с разбивкой на backend/frontend задачи по фазам, dependencies и AC для QA.
