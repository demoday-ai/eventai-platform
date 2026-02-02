# API Inventory: AI-first Unconference Navigator

> Версия: 1.1
> Дата: 2 февраля 2026
> Основано на: USM v2.1, ER v1.1, RICE v4.0
> Базовый URL: `https://api.example.com/v1`

## Обзор

**Всего endpoints:** 72 (+10 от v1.0)
**API Style:** REST
**Формат:** JSON
**Авторизация:** Bearer Token (role-based)

### Роли доступа

| Роль | Код | Описание |
|---|---|---|
| Public | — | Без авторизации |
| Auth | any | Любой авторизованный пользователь |
| Organizer | organizer | Организатор |
| Student | student | Студент/участник |
| Expert | expert | Эксперт/жюри |
| Guest | guest | Гость |
| Business | business | Бизнес/партнёр |
| Admin | organizer | Организатор с админ-правами |

### Сводка по доменам

| Домен | Endpoints | Описание |
|---|---|---|
| Auth | 3 | Аутентификация и профиль текущего пользователя |
| Users | 5 | Пользователи и роли |
| Events | 6 | События и расписание |
| Projects | 10 | Проекты, материалы, теги |
| Matching | 6 | Профиль интересов, рекомендации, подтипы |
| Business Profiles | 3 | Бизнес-профилирование (H14) |
| QA Suggestions | 2 | Q&A-подсказки (H10) |
| Shortlists | 3 | Избранные проекты пользователя |
| Participation | 5 | Заявки и подтверждения |
| Reviews | 5 | Оценки проектов |
| Feedback | 3 | Обратная связь гостей/бизнеса |
| Contacts | 3 | Запросы контакта |
| Notifications | 3 | Напоминания и follow-up |
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
| GET | /profile/interests | Auth | Профиль интересов (теги + keywords) |
| POST | /profile/interests | Auth | Создать интересы (шаг 1: теги из кнопок) |
| POST | /profile/interests/keywords | Auth | Добавить ключевые слова (шаг 2: свободный текст) |
| PATCH | /profile/interests | Auth | Уточнение интересов |
| PATCH | /users/me | Auth | Обновить guest_subtype (H16) |
| GET | /recommendations | Auth | Рекомендованные проекты |

## 6. Business Profiles (NEW, H14)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /business-profiles | Business | Создать бизнес-профиль (отрасль, формат, стадия) |
| GET | /business-profiles/me | Business | Мой бизнес-профиль |
| PATCH | /business-profiles/me | Business | Обновить бизнес-профиль |

## 7. QA Suggestions (NEW, H10)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /qa-suggestions | Guest, Business | Сгенерировать Q&A-подсказки по проекту |
| GET | /qa-suggestions | Guest, Business | Мои Q&A-подсказки (список) |

**Примечание:** Q&A-подсказки доступны только ролям Гость и Бизнес/партнёр. Эксперты формулируют вопросы самостоятельно (CustDev интервью #2).

## 8. Shortlists

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /shortlists | Auth | Список избранных проектов |
| POST | /shortlists | Auth | Добавить проект в избранное |
| DELETE | /shortlists/{id} | Auth | Удалить из избранного |

## 9. Participation

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /participation-requests | Student, Expert | Подать заявку/подтвердить участие |
| GET | /participation-requests | Admin | Список заявок |
| PATCH | /participation-requests/{id} | Admin | Подтвердить/отклонить |
| GET | /participation-requests/me | Auth | Мои заявки |
| GET | /sections | Auth | Секции/комнаты |

## 10. Reviews

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /project-reviews | Expert | Оценить проект |
| GET | /project-reviews | Admin | Все оценки |
| GET | /project-reviews/me | Expert | Мои оценки |
| POST | /project-reviews/{id}/items | Expert | Оценка по критериям |
| GET | /project-reviews/{id} | Auth | Детали оценки |

## 11. Feedback

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /event-feedback | Guest, Business, Expert | Оставить фидбек |
| GET | /event-feedback | Admin | Список фидбека |
| GET | /event-feedback/me | Auth | Мой фидбек |

## 12. Contacts

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /contact-requests | Guest, Business, Expert | «Хочу контакт» по проекту |
| GET | /contact-requests | Admin | Список запросов |
| PATCH | /contact-requests/{id} | Admin | Одобрить/отклонить запрос контакта |

**Примечание:** Это запрос контактных данных, НЕ запись на 1:1 встречу (H15 депр., RICE 12).

## 13. Notifications

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /notifications | Admin | Список уведомлений |
| POST | /notifications | Admin | Создать уведомление |
| PATCH | /notifications/{id} | Admin | Отменить/перенести |

## 14. Invites

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /role-invites | Admin | Создать приглашение на роль |
| POST | /role-invites/accept | Auth | Принять приглашение по коду |
| POST | /access-requests | Auth | Запросить назначение роли организатора |
| GET | /access-requests | Admin | Список запросов доступа |
| PATCH | /access-requests/{id} | Admin | Одобрить/отклонить запрос |

## 15. Admin

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

### Изменения v1.0 → v1.1

| Что изменено | Описание |
|---|---|
| Matching домен | +2 endpoints: `/profile/interests/keywords`, `PATCH /users/me` (guest_subtype) |
| Business Profiles | **Новый домен** (+3): POST/GET/PATCH бизнес-профиля (H14) |
| QA Suggestions | **Новый домен** (+2): POST/GET Q&A-подсказок (H10) |
| Contacts | +1 endpoint: PATCH для модерации запросов |
| Роли доступа | Уточнены: Guest, Business, Student, Expert (вместо общего Auth) |
| Participation | Уточнено: Student + Expert (не все роли) |
| Feedback | Уточнено: Guest + Business + Expert |
| Источники | USM v1 → v2.1, ER v1 → v1.1 |
