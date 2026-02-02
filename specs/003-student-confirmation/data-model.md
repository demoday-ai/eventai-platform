# Data Model: Подтверждение участия студентов

**Date**: 2026-02-02

## New Entity: ParticipationRequest

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto | Уникальный идентификатор |
| event_id | UUID | FK → events.id, NOT NULL | Событие (Demo Day) |
| project_id | UUID | FK → projects.id, NOT NULL | Проект студента |
| room_project_id | UUID | FK → room_projects.id, NULL | Привязка к залу (из кластеризации). NULL если расписание ещё не утверждено |
| user_id | UUID | FK → users.id, NOT NULL | Студент (автор проекта) |
| status | ENUM | NOT NULL, default='pending' | pending → sent → confirmed / declined |
| proposed_time | TIMESTAMP | NULL | Предложенное время слота |
| decline_reason | TEXT | NULL | Причина отказа (опциональная) |
| reminder_sent_at | TIMESTAMP | NULL | Когда отправлено напоминание |
| escalated_at | TIMESTAMP | NULL | Когда эскалировано организатору |
| confirmed_at | TIMESTAMP | NULL | Когда подтверждено/отклонено |
| telegram_message_id | BIGINT | NULL | ID отправленного сообщения (для edit) |
| created_at | TIMESTAMP | NOT NULL, auto | Время создания |

### Status State Machine

```
pending → sent → confirmed
                → declined
                → (no response) → reminded → escalated
```

- **pending**: запрос создан, сообщение ещё не отправлено
- **sent**: сообщение отправлено студенту
- **confirmed**: студент нажал "Подтверждаю"
- **declined**: студент нажал "Не смогу"
- **reminded**: повторное напоминание отправлено (через 3 дня)
- **escalated**: организатор уведомлён (через 5 дней)

### Constraints

- UNIQUE(event_id, project_id) — один запрос на проект за событие
- Статус может переходить: confirmed ↔ declined (студент может передумать)
- При изменении расписания: статус сбрасывается на `sent`, telegram_message_id обновляется

## Relationships

```
Event 1──N ParticipationRequest
Project 1──1 ParticipationRequest (per event)
User 1──N ParticipationRequest
RoomProject 1──1 ParticipationRequest (optional)
```

## Existing Models Used (no changes)

- **User**: telegram_user_id для отправки сообщений
- **Project**: title, author, telegram_contact для формирования сообщения
- **Room**: name для "Зал 3"
- **RoomProject**: связь проект-зал из кластеризации
- **Event**: даты DD для расчёта дедлайнов эскалации
- **ClusteringRun**: status='done' + approved_at → триггер для создания ParticipationRequest
