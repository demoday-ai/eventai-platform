# Навык: API Inventory

## Цель

Создать структурированный список всех API endpoints системы на основе User Story Map. Лёгкий артефакт для планирования — не OpenAPI спецификация, а обзор того, какие endpoints нужны.

---

## Входные данные

**Обязательно:**
- User Story Map (источник функциональности)

**Опционально:**
- ER Diagram (какие ресурсы)
- C4 Container (какие сервисы предоставляют API)

---

## Процесс

### Шаг 1: Извлечение ресурсов

Из USM — основные ресурсы (существительные): Users, Orders, Tasks, Projects...

### Шаг 2: Маппинг User Stories → Endpoints

| User Story | Endpoint |
|------------|----------|
| Видеть список задач | `GET /tasks` |
| Создать задачу | `POST /tasks` |
| Изменить статус | `PATCH /tasks/{id}` |
| Удалить задачу | `DELETE /tasks/{id}` |
| Комментарии к задаче | `GET /tasks/{id}/comments` |

### Шаг 3: Группировка по доменам

Auth, Users, [Domain], Admin, Webhooks

---

## Формат API Inventory

### Компактная таблица

```markdown
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /auth/register | Public | Регистрация |
| POST | /auth/login | Public | Вход |
| GET | /users/me | Auth | Текущий пользователь |
```

### Детальный формат (для критичных endpoints)

```markdown
### `POST /auth/register`

**Назначение:** Регистрация
**User Story:** US-001
**Авторизация:** Public

**Request Body:**
- email, password, name

**Responses:**
- `201` — создан
- `400` — невалидные данные
- `409` — email занят
```

---

## Целевая структура вывода

```markdown
# API Inventory: [Название]

> Основано на: USM v[X]
> Базовый URL: `https://api.example.com/v1`

## Обзор

**Всего endpoints:** N
**API Style:** REST
**Формат:** JSON
**Авторизация:** Bearer JWT

### Сводка по доменам

| Домен | Endpoints | Описание |
|-------|-----------|----------|

## 1. Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|

[Детали критичных endpoints]

## 2. Users

[...]

## Приложения

### Коды ошибок

| Code | Description |
|------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Business error |
| 429 | Rate limit |

### Формат ошибки

{ "error": { "code": "...", "message": "...", "details": [...] } }

### Пагинация

?page=N&limit=N
Response: { "pagination": { "page", "limit", "total", "pages" } }
```

---

## Pro-tips

- **Это не OpenAPI** — для планирования, не для генерации клиентов
- **Детализируй критичные** — Auth и основные CRUD подробно
- **Остальные кратко** — таблицы достаточно для scope
- **Консистентность** — одинаковые паттерны для одинаковых операций
- **Версионирование** — `/v1/` в URL
- **HATEOAS не нужен** — для MVP overkill
- **Webhook endpoints** — не забывай входящие webhooks (Stripe, Slack)
