# Data Model: Ознакомление студентов с расписанием

**Date**: 2026-02-02 (updated after clarify)

## New Entity: ParticipationRequest

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto | Уникальный идентификатор |
| event_id | UUID | FK → events.id, NOT NULL | Событие (Demo Day) |
| project_id | UUID | FK → projects.id, NOT NULL | Проект студента |
| room_project_id | UUID | FK → room_projects.id, NULL | Привязка к залу (из кластеризации). NULL если расписание ещё не утверждено |
| user_id | UUID | FK → users.id, NULL | Студент (автор проекта). NULL если студент не зарегистрирован в боте |
| status | ENUM | NOT NULL, default='pending' | pending → sent → acknowledged |
| reminder_sent_at | TIMESTAMP | NULL | Когда отправлено напоминание (за 5 дней до DD) |
| escalated_at | TIMESTAMP | NULL | Когда эскалировано организатору (за 2 дня до DD) |
| acknowledged_at | TIMESTAMP | NULL | Когда студент нажал "Ознакомлен" |
| telegram_message_id | BIGINT | NULL | ID отправленного сообщения (для edit) |
| created_at | TIMESTAMP | NOT NULL, auto | Время создания |

### Status State Machine

```
pending → sent → acknowledged
              → (no response, DD-5d) → reminded (flag)
              → (no response, DD-2d) → escalated (flag)
```

- **pending**: запрос создан, сообщение ещё не отправлено
- **sent**: сообщение отправлено студенту
- **acknowledged**: студент нажал "Ознакомлен"

Дополнительные флаги (не влияют на status enum):
- **reminder_sent_at** ≠ NULL → напоминание отправлено
- **escalated_at** ≠ NULL → организатор уведомлён

### Constraints

- UNIQUE(event_id, project_id) — один запрос на проект за событие
- При изменении расписания (room_project_id изменился): статус сбрасывается на `sent`, acknowledged_at = NULL, reminder_sent_at = NULL, отправляется новое сообщение

### Enum: ParticipationStatus

```python
class ParticipationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
```

## Relationships

```
Event 1──N ParticipationRequest
Project 1──1 ParticipationRequest (per event)
User 1──N ParticipationRequest (nullable — студент может быть не зарегистрирован)
RoomProject 1──1 ParticipationRequest (nullable — расписание может быть не утверждено)
```

## Existing Models Used (no changes)

- **User**: telegram_user_id для отправки сообщений, username для матчинга с project.telegram_contact
- **Project**: title, author, telegram_contact для формирования сообщения
- **Room**: name, display_order для "Зал 3"
- **RoomProject**: связь проект-зал из кластеризации
- **Event**: start_date для расчёта дедлайнов (DD-5d = напоминание, DD-2d = эскалация)
- **ClusteringRun**: status + approved_at → триггер для возможности создания ParticipationRequest

## Migration: 005_participation_requests.py

```
Revision: 005
Down revision: 004 (guest_profiling)

Operations:
1. CREATE TYPE participation_status_enum AS ENUM ('pending', 'sent', 'acknowledged')
2. CREATE TABLE participation_requests (
     id UUID PK DEFAULT gen_random_uuid(),
     event_id UUID FK NOT NULL REFERENCES events(id) ON DELETE CASCADE,
     project_id UUID FK NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
     room_project_id UUID FK NULL REFERENCES room_projects(id) ON DELETE SET NULL,
     user_id UUID FK NULL REFERENCES users(id) ON DELETE SET NULL,
     status participation_status_enum NOT NULL DEFAULT 'pending',
     reminder_sent_at TIMESTAMPTZ NULL,
     escalated_at TIMESTAMPTZ NULL,
     acknowledged_at TIMESTAMPTZ NULL,
     telegram_message_id BIGINT NULL,
     created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
     CONSTRAINT uq_participation_event_project UNIQUE(event_id, project_id)
   )
3. CREATE INDEX ix_participation_requests_event_status ON participation_requests(event_id, status)
4. CREATE INDEX ix_participation_requests_user ON participation_requests(user_id)
```
