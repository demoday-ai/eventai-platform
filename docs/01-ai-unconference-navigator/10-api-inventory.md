# API Inventory: AI-first Unconference Navigator

> Основано на: USM v1, ER v1  
> Базовый URL: `https://api.example.com/v1`

## Обзор

**Всего endpoints:** 62  
**API Style:** REST  
**Формат:** JSON  
**Авторизация:** Bearer Token (role-based)

### Сводка по доменам

| Домен | Endpoints | Описание |
|---|---|---|
| Auth | 3 | Аутентификация и профиль текущего пользователя |
| Users | 5 | Пользователи и роли |
| Events | 6 | События и расписание |
| Projects | 10 | Проекты, материалы, теги |
| Matching | 4 | Профиль интересов и рекомендации |
| Shortlists | 3 | Избранные проекты пользователя |
| Participation | 5 | Заявки и подтверждения |
| Reviews | 5 | Оценки проектов |
| Feedback | 3 | Обратная связь гостей |
| Contacts | 2 | Запросы контакта |
| Notifications | 3 | Напоминания и follow‑up |
| Invites | 5 | Приглашения и запросы доступа |
| Admin | 8 | Сводки и управление расписанием |

---

## 1. Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /auth/login | Public | Вход по коду/ссылке (Telegram) |
| POST | /auth/refresh | Auth | Обновление токена |
| GET | /auth/me | Auth | Текущий пользователь |

## 2. Users

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /users | Admin | Список пользователей |
| GET | /users/{id} | Admin | Профиль пользователя |
| PATCH | /users/{id} | Admin | Обновить профиль |
| GET | /users/{id}/roles | Admin | Роли пользователя в событии |
| PUT | /users/{id}/roles | Admin | Назначение роли |

## 3. Events

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /events | Auth | Список событий |
| POST | /events | Admin | Создать событие |
| GET | /events/{id} | Auth | Детали события |
| PATCH | /events/{id} | Admin | Обновить событие |
| GET | /events/{id}/schedule | Auth | Расписание (секции/сессии) |
| GET | /events/{id}/stats | Admin | Статусы подтверждений и покрытие |

## 4. Projects

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /events/{id}/projects | Auth | Список проектов в событии |
| POST | /events/{id}/projects | Admin | Добавить проект |
| GET | /projects/{id} | Auth | Карточка проекта |
| PATCH | /projects/{id} | Admin | Обновить проект |
| POST | /projects/{id}/materials | Auth | Добавить материал проекта |
| GET | /projects/{id}/materials | Auth | Материалы проекта |
| POST | /projects/{id}/tags | Admin | Привязать теги |
| GET | /projects/{id}/tags | Auth | Теги проекта |
| GET | /projects/{id}/sessions | Auth | Сессии проекта |
| POST | /projects/{id}/sessions | Admin | Привязать проект к сессии |

## 5. Matching

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /profile/interests | Auth | Профиль интересов |
| POST | /profile/interests | Auth | Создать/обновить интересы |
| PATCH | /profile/interests | Auth | Уточнение интересов |
| GET | /recommendations | Auth | Рекомендованные проекты |

## 6. Shortlists

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /shortlists | Auth | Список избранных проектов |
| POST | /shortlists | Auth | Добавить проект в избранное |
| DELETE | /shortlists/{id} | Auth | Удалить из избранного |

## 7. Participation

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /participation-requests | Auth | Подать заявку/подтвердить участие |
| GET | /participation-requests | Admin | Список заявок |
| PATCH | /participation-requests/{id} | Admin | Подтвердить/отклонить |
| GET | /participation-requests/me | Auth | Мои заявки |
| GET | /sections | Auth | Секции/комнаты |

## 8. Reviews

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /project-reviews | Expert | Оценить проект |
| GET | /project-reviews | Admin | Все оценки |
| GET | /project-reviews/me | Expert | Мои оценки |
| POST | /project-reviews/{id}/items | Expert | Оценка по критериям |
| GET | /project-reviews/{id} | Auth | Детали оценки |

## 9. Feedback

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /event-feedback | Auth | Оставить фидбек |
| GET | /event-feedback | Admin | Список фидбека |
| GET | /event-feedback/me | Auth | Мой фидбек |

## 10. Contacts

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /contact-requests | Auth | “Хочу контакт” |
| GET | /contact-requests | Admin | Список запросов |

## 11. Notifications

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /notifications | Admin | Список уведомлений |
| POST | /notifications | Admin | Создать уведомление |
| PATCH | /notifications/{id} | Admin | Отменить/перенести |

## 12. Invites

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /role-invites | Admin | Создать приглашение на роль |
| POST | /role-invites/accept | Auth | Принять приглашение по коду |
| POST | /access-requests | Auth | Запросить назначение роли организатора |
| GET | /access-requests | Admin | Список запросов доступа |
| PATCH | /access-requests/{id} | Admin | Одобрить/отклонить запрос |

## 13. Admin

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /admin/coverage | Admin | Покрытие тематик/секций |
| GET | /admin/confirmations | Admin | Доля подтверждений |
| POST | /admin/tracks | Admin | Создать трек |
| PATCH | /admin/tracks/{id} | Admin | Обновить трек |
| POST | /admin/sections | Admin | Создать секцию |
| PATCH | /admin/sections/{id} | Admin | Обновить секцию |
| POST | /admin/sessions | Admin | Создать сессию |
| PATCH | /admin/sessions/{id} | Admin | Обновить сессию |

---

## Приложения

### Коды ошибок

| Code | Description |
|---|---|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Business error |
| 429 | Rate limit |

### Формат ошибки

```json
{ "error": { "code": "...", "message": "...", "details": [] } }
```

### Пагинация

`?page=N&limit=N`

```json
{ "pagination": { "page": 1, "limit": 20, "total": 0, "pages": 0 } }
```
