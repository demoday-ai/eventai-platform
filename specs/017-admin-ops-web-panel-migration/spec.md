# Specification: Admin Ops Migration (Telegram -> Web Admin)

**Version:** 0.1  
**Date:** 2026-02-04  
**Status:** Draft  
**Target branch:** `frontend` (UI) + `main` (backend API gaps)

---

## 1) Goal

Перенести администраторские операции из Telegram-бота в web админ-панель, максимально переиспользуя уже реализованный backend/бот функционал, и закрыть API gaps для операций, которых пока нет в web-потоке.

---

## 2) Scope (по запросу)

Нужно реализовать в админ-панели:

1. Загрузка документа с выступающими, темами, контактами.
2. Загрузка списка TG-контактов и имён бизнес-партнёров и экспертов, от которых нужны оценки.
3. Кнопки отправки Telegram-сообщений партнёрам (со ссылкой / без ссылки).
4. Ручная отправка оповещений.
5. Выбор дат конференции.
6. Ручное добавление организаторов.
7. Ручное добавление экспертов.

---

## 3) Что уже реализовано (reuse baseline)

### 3.1 Admin/web базовые endpoints
- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/coverage`
- `GET /api/v1/admin/rooms/{room_id}`
- `GET /api/v1/admin/projects`

Файлы: `backend/app/api/admin.py`, `backend/app/services/admin_service.py`.

### 3.2 Операции из Telegram, уже покрытые API
- **Загрузка проектов/выступающих**: `POST /api/v1/projects/upload` (CSV/JSON).
- **Загрузка экспертов**: `POST /api/v1/experts/upload` (JSON).
- **Ручные рассылки/оповещения**:
  - `POST /api/v1/participation/broadcast`
  - `POST /api/v1/reminders/send`
  - `GET /api/v1/reminders/preview`
  - `POST /api/v1/reminders/cancel`

Файлы: `backend/app/api/projects.py`, `backend/app/api/experts.py`, `backend/app/api/participation.py`, `backend/app/api/schedule.py`.

### 3.3 Ограничения текущей реализации
- Для **бизнес-партнёров** нет отдельного admin upload endpoint (bulk import).
- Нет отдельного admin endpoint для «отправить партнёрам сообщение (с/без ссылок)».
- Даты события (`events.start_date/end_date`) не редактируются через admin API.
- Организаторы сейчас задаются через `ORGANIZER_TELEGRAM_IDS` (env), без CRUD в UI.
- Ручное добавление эксперта единично (create form) отсутствует, есть только bulk upload.

---

## 4) Mapping: требование -> текущая база -> gap

| # | Требование | Что уже есть | Gap |
|---|------------|--------------|-----|
| 1 | Upload выступающих/тем/контактов | `POST /projects/upload` + validation | Нужен web UI-экран + UX ошибок/дубликатов |
| 2 | Upload партнёров и экспертов | Эксперты: `POST /experts/upload` | Для партнёров нужен новый upload endpoint + сущность/схема |
| 3 | Telegram сообщения партнёрам (с/без ссылок) | Частично есть рассылки в других потоках | Нужен отдельный admin messaging flow для partner сегмента |
| 4 | Ручная отправка оповещений | `participation/broadcast`, `reminders/send` | Нужен единый web control center |
| 5 | Выбор дат конференции | Event даты есть в модели | Нужен admin endpoint для update дат + UI |
| 6 | Ручное добавление организаторов | Ограничение через env и роль | Нужен organizer management (UI + API) |
| 7 | Ручное добавление экспертов | Bulk upload экспертов | Нужен single create/edit form (или inline add) |

---

## 5) Target UX в web admin

Новые разделы в админке:

1. **Data Import**
   - Upload projects (CSV/JSON)
   - Upload experts (JSON)
   - Upload partners (CSV/JSON) [new]
2. **Messaging**
   - Шаблон сообщения для партнёров
   - Переключатель: `with_links` / `without_links`
   - Preview + Send
3. **Notifications**
   - Кнопки ручного запуска: participation broadcast, reminders send
   - Просмотр статусов отправки
4. **Conference Settings**
   - Изменение `start_date`, `end_date`
5. **Access Management**
   - Список/добавление/удаление организаторов
6. **Experts Management**
   - Ручное добавление эксперта (single create)
   - Редактирование контакта/тегов

---

## 6) API plan (reuse-first)

## 6.1 Используем без изменений
- `POST /api/v1/projects/upload`
- `POST /api/v1/experts/upload`
- `POST /api/v1/participation/broadcast`
- `GET/POST /api/v1/reminders/*`
- `GET /api/v1/admin/*` (dashboard/coverage/rooms/projects)

## 6.2 Добавляем новые endpoints

### A) Partners import
- `POST /api/v1/admin/partners/upload`
  - Input: CSV/JSON (`name`, `telegram_contact`, `company`, `role`, optional tags)
  - Output: parsed/imported/errors/duplicates summary

### B) Partner messaging
- `POST /api/v1/admin/partners/messages/preview`
  - Input: template, `include_links: bool`, filters
- `POST /api/v1/admin/partners/messages/send`
  - Input: same + optional dry_run
  - Output: sent/failed/skipped

### C) Conference dates
- `PATCH /api/v1/admin/events/current`
  - Input: `start_date`, `end_date`

### D) Organizers management
- `GET /api/v1/admin/organizers`
- `POST /api/v1/admin/organizers`
- `DELETE /api/v1/admin/organizers/{telegram_id}`

### E) Experts management (single create)
- `POST /api/v1/admin/experts`
  - Input: name, telegram, position, tags

---

## 7) Delivery plan (phases)

### Phase 1 (MVP, reuse-only, быстрый выход)
- Web screens поверх уже существующих endpoint:
  - Upload projects
  - Upload experts
  - Manual send notifications (participation/reminders)
- Критерий: админ больше не выполняет эти операции в Telegram.

### Phase 2 (API gaps)
- Реализация endpoints для:
  - partners upload
  - partner messaging with/without links
  - conference dates update
  - organizers CRUD
  - expert single create

### Phase 3 (hardening)
- Аудит-лог admin действий
- Retry/observability по отправкам
- Валидации и anti-duplication для импортов
- Ролевой контроль доступа (organizer-only для новых операций)

---

## 8) Acceptance criteria по 7 функциям

1. **Upload projects**
   - Админ загружает файл из web UI и видит summary (`loaded/errors/duplicates`).
2. **Upload partners + experts**
   - Эксперты грузятся через UI на существующий endpoint.
   - Партнёры грузятся через новый endpoint с аналогичным summary.
3. **Partner messaging buttons**
   - В UI есть два режима отправки: со ссылкой и без ссылки.
4. **Manual notifications**
   - Из UI запускаются существующие ручные рассылки и виден результат.
5. **Conference dates**
   - Даты события редактируются из UI, изменения отражаются в API.
6. **Manual organizers add**
   - Организатор может добавить/удалить organizer ID без правки env.
7. **Manual experts add**
   - Эксперт добавляется вручную через форму без bulk файла.

---

## 9) Risks

- Рассинхрон ролей (env vs DB) при переходе на organizers CRUD.
- Неоднозначность модели business partner (нет единой таблицы bulk-списка).
- Отправка сообщений требует стабильного bot instance и контроля ошибок доставки.

---

## 10) Non-goals (для этого этапа)

- Полная замена всех Telegram user-facing сценариев.
- Реалтайм push/WebSocket панель оператора.
- Массовые BI-дашборды и advanced аналитика.

---

## 11) Рекомендуемый следующий артефакт

После согласования этого документа — создать `tasks.md` с разбивкой на backend/frontend задачи (MVP first) и AC для QA.
