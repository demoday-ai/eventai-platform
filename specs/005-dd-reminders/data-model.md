# Data Model: DD Reminders & Timing Shift Notifications (EPIC-005)

**Date**: 2026-02-02 | **Migration**: `004_dd_reminders.py`

## Overview

3 new tables. Schedule slots link approved clustering rooms to time blocks. Notifications track every message sent to participants. Schedule change logs provide audit trail for timing shifts.

## Entity Relationship

```
events (EPIC-001)
  │
  │ 1:M
  ▼
schedule_slots ──────── rooms (EPIC-002)
  │         │
  │ 1:1     │ M:1
  │         ▼
  │    room_projects (EPIC-002) ── projects (EPIC-002)
  │
  │ 1:M
  ▼
schedule_change_logs

users (EPIC-001)
  │
  │ 1:M
  ▼
notifications ──── schedule_slots (optional FK)
```

## New Tables

### 1. `schedule_slots`

A time block representing when a specific project is presented in a specific room. Auto-generated from approved clustering, adjustable by organizer.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Primary key |
| created_at | DateTime(tz) | NOT NULL, server_default now() | Created timestamp |
| updated_at | DateTime(tz) | NULLABLE, onupdate now() | Last modification |
| event_id | UUID | FK → events.id, NOT NULL | Event scope |
| room_id | UUID | FK → rooms.id, CASCADE, NOT NULL | Which room |
| project_id | UUID | FK → projects.id, CASCADE, NOT NULL | Which project |
| clustering_run_id | UUID | FK → clustering_runs.id, CASCADE, NOT NULL | Which clustering run generated this |
| start_time | DateTime(tz) | NOT NULL | Slot start (Moscow time) |
| end_time | DateTime(tz) | NOT NULL | Slot end (Moscow time) |
| display_order | INTEGER | NOT NULL, default 0 | Order within room (for rendering) |
| status | VARCHAR(20) | NOT NULL, default 'scheduled' | Slot status |
| status_changed_at | DateTime(tz) | NULLABLE | When status last changed |

**Unique constraint**: `(project_id, clustering_run_id)` — one slot per project per clustering run

**Status enum values**:
- `scheduled` — normal active slot
- `moved` — time or room was changed (old slot marked, new slot created)
- `cancelled` — project removed from schedule

**State transitions**:
```
scheduled → moved (organizer changes time/room → old slot marked "moved", new slot created)
scheduled → cancelled (organizer cancels project)
cancelled → scheduled (organizer restores project)
```

**Relationships**:
- `schedule_slot.event` → Event
- `schedule_slot.room` → Room
- `schedule_slot.project` → Project
- `schedule_slot.change_logs` → 1:M to ScheduleChangeLog
- `schedule_slot.notifications` → 1:M to Notification

### 2. `notifications`

Record of every message sent (or attempted) to a participant. Used for dedup, retry tracking, and the organizer dashboard.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Primary key |
| created_at | DateTime(tz) | NOT NULL, server_default now() | When notification was created/queued |
| event_id | UUID | FK → events.id, NOT NULL | Event scope |
| user_id | UUID | FK → users.id, CASCADE, NOT NULL | Recipient |
| schedule_slot_id | UUID | FK → schedule_slots.id, NULLABLE | Related slot (NULL for eve-of-DD bulk reminders) |
| type | VARCHAR(30) | NOT NULL | Notification type |
| content | TEXT | NOT NULL | Message text sent to user |
| status | VARCHAR(20) | NOT NULL, default 'pending' | Delivery status |
| scheduled_at | DateTime(tz) | NULLABLE | When notification is scheduled to be sent |
| sent_at | DateTime(tz) | NULLABLE | When actually sent |
| retry_count | INTEGER | NOT NULL, default 0 | Number of send attempts |
| error_message | TEXT | NULLABLE | Last error if failed |
| batch_key | VARCHAR(100) | NULLABLE | For batching timing shift notifications |

**Type enum values**:
- `eve_of_dd` — day-before reminder
- `pre_slot` — 1-hour-before reminder
- `timing_shift` — schedule change notification
- `program_cancelled` — all program items cancelled

**Status enum values**:
- `pending` — queued, not yet sent
- `sent` — successfully delivered to Telegram API
- `failed` — all retries exhausted
- `cancelled` — organizer cancelled the send
- `batched` — merged into another notification (original kept for audit)

**State transitions**:
```
pending → sent (successful delivery)
pending → failed (3 retries exhausted)
pending → cancelled (organizer cancelled eve-of-DD send)
pending → batched (merged into batch notification)
```

**Relationships**:
- `notification.user` → User
- `notification.event` → Event
- `notification.schedule_slot` → ScheduleSlot (nullable)

### 3. `schedule_change_logs`

Audit trail recording every modification to schedule slots. Used for timing shift notification content (old vs new time).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Primary key |
| created_at | DateTime(tz) | NOT NULL, server_default now() | When change was made |
| schedule_slot_id | UUID | FK → schedule_slots.id, CASCADE, NOT NULL | Which slot changed |
| event_id | UUID | FK → events.id, NOT NULL | Event scope |
| changed_by_user_id | UUID | FK → users.id, NULLABLE | Organizer who made the change |
| change_type | VARCHAR(20) | NOT NULL | Type of change |
| old_start_time | DateTime(tz) | NULLABLE | Previous start time |
| old_end_time | DateTime(tz) | NULLABLE | Previous end time |
| old_room_id | UUID | FK → rooms.id, NULLABLE | Previous room |
| new_start_time | DateTime(tz) | NULLABLE | New start time |
| new_end_time | DateTime(tz) | NULLABLE | New end time |
| new_room_id | UUID | FK → rooms.id, NULLABLE | New room |
| notifications_sent | BOOLEAN | NOT NULL, default false | Whether affected participants were notified |

**Change type enum values**:
- `time_changed` — start/end time modified
- `room_changed` — moved to different room
- `time_and_room_changed` — both changed
- `cancelled` — slot cancelled
- `restored` — slot restored from cancelled

**Relationships**:
- `schedule_change_log.schedule_slot` → ScheduleSlot
- `schedule_change_log.changed_by` → User (organizer)
- `schedule_change_log.old_room` → Room
- `schedule_change_log.new_room` → Room

## Reused Tables (no changes)

| Table | From | Used for |
|-------|------|----------|
| `events` | EPIC-001 | Event scope, start_date/end_date for schedule generation |
| `users` | EPIC-001 | Notification recipients (telegram_user_id for sending) |
| `rooms` | EPIC-002 | Room assignments for schedule slots |
| `projects` | EPIC-002 | Project assignments for schedule slots |
| `room_projects` | EPIC-002 | Source data for auto-generating schedule slots |
| `clustering_runs` | EPIC-002 | Approved clustering as basis for schedule; extended with `schedule_approved_at` |
| `escalations` | EPIC-004 | Extended with new types for notification failures |

## Extended Tables (schema changes)

### `clustering_runs` — new column for schedule approval

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| schedule_approved_at | TIMESTAMP WITH TIME ZONE | NULLABLE | When organizer approved the generated schedule; NULL = not yet approved |

**Rationale**: Reuses existing table rather than creating separate approval tracking. Schedule generation creates slots from a clustering_run; approval is a property of that run. Migration `004_dd_reminders.py` adds this column.

## Extended Tables (minor changes)

### `escalations` — new type values only (no schema change)

New `type` values added in service layer:
- `notification_undeliverable` — participant never started bot
- `reminder_send_failed` — Telegram API error after 3 retries

The `expert_id` field is already nullable in the model. For non-expert escalations, `expert_id` will be NULL and we reference the user via the notification record. The `room_id` will reference the affected room (or NULL for generic failures).

## Indexes

```sql
-- Schedule slot lookups
CREATE INDEX ix_schedule_slots_event_id ON schedule_slots(event_id);
CREATE INDEX ix_schedule_slots_room_id ON schedule_slots(room_id);
CREATE INDEX ix_schedule_slots_project_id ON schedule_slots(project_id);
CREATE INDEX ix_schedule_slots_start_time ON schedule_slots(start_time);
CREATE INDEX ix_schedule_slots_status ON schedule_slots(status);

-- Notification lookups
CREATE INDEX ix_notifications_event_id ON notifications(event_id);
CREATE INDEX ix_notifications_user_id ON notifications(user_id);
CREATE INDEX ix_notifications_type ON notifications(type);
CREATE INDEX ix_notifications_status ON notifications(status);
CREATE INDEX ix_notifications_scheduled_at ON notifications(scheduled_at);
CREATE UNIQUE INDEX ix_notifications_dedup ON notifications(user_id, schedule_slot_id, type)
    WHERE status NOT IN ('failed', 'cancelled', 'batched');

-- Schedule change log lookups
CREATE INDEX ix_schedule_change_logs_slot_id ON schedule_change_logs(schedule_slot_id);
CREATE INDEX ix_schedule_change_logs_event_id ON schedule_change_logs(event_id);
```

## Validation Rules

1. **Schedule slot times**: `start_time < end_time`. Both must fall within the event's date range.
2. **Slot duration**: Default 15 minutes. Service layer enforces `end_time - start_time == 15 min` during auto-generation; manual adjustments may vary.
3. **One slot per project per run**: DB unique constraint `(project_id, clustering_run_id)`.
4. **Notification dedup**: Partial unique index on `(user_id, schedule_slot_id, type)` excluding failed/cancelled/batched ensures no active duplicates.
5. **Retry count**: Must not exceed 3 (enforced in service layer).
6. **Status transitions**: Enforced in service layer (not DB constraints).
7. **Timezone**: All DateTime fields stored as timezone-aware (UTC internally, converted to MSK for display).

## Migration Notes

- Migration depends on: `001_initial_schema` (users, events), `002_projects_clustering` (rooms, projects, room_projects, clustering_runs), `003_expert_assignment` (escalations — for type extension)
- Creates 3 tables: schedule_slots → notifications → schedule_change_logs
- No data migration needed (schedule generated at runtime from approved clustering)
- Rollback: drop all 3 tables in reverse order
- Escalation type extension requires no schema change (type is VARCHAR, not ENUM)
