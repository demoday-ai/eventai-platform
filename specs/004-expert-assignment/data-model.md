# Data Model: Распределение экспертов (EPIC-004)

**Date**: 2026-02-02 | **Migration**: `003_expert_assignment.py`

## Overview

4 new tables + 1 reused table (`tags` from EPIC-002). Expert profiles link to existing `users` table when expert starts the bot.

## Entity Relationship

```
users (EPIC-001)          tags (EPIC-002)
  │                          │
  │ 1:1 (nullable)           │ M:M
  ▼                          ▼
experts ──────────── expert_tags
  │
  │ 1:M
  ▼
expert_room_assignments ──── rooms (EPIC-002)
  │                            │
  │                            │
  ▼                            ▼
escalations            clustering_runs (EPIC-002)
```

## New Tables

### 1. `experts`

Expert profile. Pre-loaded from seed, linked to `users` when expert starts bot.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Primary key |
| created_at | DateTime(tz) | NOT NULL, server_default now() | Created timestamp |
| seed_id | VARCHAR(20) | UNIQUE, NOT NULL | External ID from seed (e.g. "EXP-001") |
| name | VARCHAR(200) | NOT NULL | Full name from seed |
| telegram_username | VARCHAR(100) | NULLABLE | Telegram @username (without @) |
| position | VARCHAR(300) | NULLABLE | Role/company from seed |
| inviter | VARCHAR(100) | NULLABLE | Who invited this expert |
| dd_status_seed | VARCHAR(50) | NULLABLE | DD status from seed ("Придет", "Ждем ответ", etc.) |
| user_id | UUID | FK → users.id, NULLABLE, UNIQUE | Link to registered User (set on /start) |
| event_id | UUID | FK → events.id, NOT NULL | Event scope |
| bot_started | BOOLEAN | NOT NULL, default false | Whether expert has started bot dialog |
| bot_started_at | DateTime(tz) | NULLABLE | When expert first started bot |

**Unique constraint**: `(seed_id, event_id)`

**Relationships**:
- `expert.tags` → M2M through `expert_tags` → `tags`
- `expert.user` → nullable 1:1 to `users`
- `expert.assignments` → 1:M to `expert_room_assignments`

### 2. `expert_tags`

M2M junction between experts and tags (reuses `tags` table from EPIC-002).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Primary key |
| created_at | DateTime(tz) | NOT NULL, server_default now() | Created timestamp |
| expert_id | UUID | FK → experts.id, CASCADE, NOT NULL | Expert |
| tag_id | UUID | FK → tags.id, CASCADE, NOT NULL | Tag |

**Unique constraint**: `(expert_id, tag_id)`

### 3. `expert_room_assignments`

Assignment of expert to a room. Tracks matching score, confirmation status, manual override.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Primary key |
| created_at | DateTime(tz) | NOT NULL, server_default now() | Created timestamp |
| updated_at | DateTime(tz) | NULLABLE, onupdate now() | Last status change |
| expert_id | UUID | FK → experts.id, CASCADE, NOT NULL | Expert |
| room_id | UUID | FK → rooms.id, CASCADE, NOT NULL | Assigned room |
| clustering_run_id | UUID | FK → clustering_runs.id, CASCADE, NOT NULL | Which clustering run |
| match_score | FLOAT | NOT NULL, default 0.0 | Weighted tag-overlap score |
| is_manual | BOOLEAN | NOT NULL, default false | Manually assigned by organizer |
| status | VARCHAR(20) | NOT NULL, default 'proposed' | Assignment status |
| status_changed_at | DateTime(tz) | NULLABLE | When status last changed |
| invite_viewed_at | DateTime(tz) | NULLABLE | When expert saw invite in bot |
| reminder_count | INTEGER | NOT NULL, default 0 | Number of reminders sent |
| last_reminder_at | DateTime(tz) | NULLABLE | When last reminder was sent |

**Unique constraint**: `(expert_id, clustering_run_id)` — one assignment per expert per run

**Status enum values**:
- `proposed` — system proposed, organizer hasn't approved yet
- `approved` — organizer approved the full distribution
- `invite_ready` — organizer confirmed sending invites
- `invited` — expert opened bot and saw the invite
- `confirmed` — expert clicked "Иду"
- `declined` — expert clicked "Не смогу"
- `reassign_requested` — expert clicked "Хочу другую комнату"
- `no_show` — organizer marked no-show on DD day

**State transitions**:
```
proposed → approved (organizer approves distribution)
approved → invite_ready (organizer confirms invite sending)
invite_ready → invited (expert opens bot and sees invite)
invited → confirmed | declined | reassign_requested (expert responds)
reassign_requested → confirmed | declined (expert picks new room or declines)
confirmed → no_show (organizer marks on DD day)
Any status → approved (organizer moves expert manually, resets)
```

### 4. `escalations`

Tracks escalation events for organizer attention.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Primary key |
| created_at | DateTime(tz) | NOT NULL, server_default now() | When escalation was created |
| expert_id | UUID | FK → experts.id, CASCADE, NOT NULL | Expert who triggered escalation |
| room_id | UUID | FK → rooms.id, CASCADE, NOT NULL | Affected room |
| event_id | UUID | FK → events.id, CASCADE, NOT NULL | Event scope |
| type | VARCHAR(30) | NOT NULL | Escalation type |
| message | TEXT | NOT NULL | Human-readable description |
| resolved | BOOLEAN | NOT NULL, default false | Whether resolved by organizer |
| resolved_at | DateTime(tz) | NULLABLE | When resolved |

**Type enum values**:
- `no_response_reminder` — expert didn't respond after 3 days (reminder sent to those in bot)
- `no_response_escalation` — expert didn't respond after 5 days (alerted to organizer)
- `room_uncovered` — room has 0 confirmed experts
- `room_partially_covered` — room has only 1 confirmed expert
- `decline_impact` — expert declined, room coverage dropped

## Reused Tables (no changes)

| Table | From | Used for |
|-------|------|----------|
| `tags` | EPIC-002 | Expert expertise tags (same taxonomy as project tags) |
| `rooms` | EPIC-002 | Room assignments target |
| `clustering_runs` | EPIC-002 | FK scope for assignments |
| `users` | EPIC-001 | Link expert to registered user |
| `events` | EPIC-001 | Event scope |

## Indexes

```sql
-- Lookup expert by telegram username (for /start recognition)
CREATE INDEX ix_experts_telegram_username ON experts(telegram_username);

-- Lookup expert by seed_id (for data import)
CREATE INDEX ix_experts_seed_id ON experts(seed_id);

-- Assignment lookups
CREATE INDEX ix_era_clustering_run_id ON expert_room_assignments(clustering_run_id);
CREATE INDEX ix_era_room_id ON expert_room_assignments(room_id);
CREATE INDEX ix_era_status ON expert_room_assignments(status);

-- Escalation lookups
CREATE INDEX ix_escalations_event_id ON escalations(event_id);
CREATE INDEX ix_escalations_resolved ON escalations(resolved);
```

## Validation Rules

1. **Expert seed_id**: Must be unique per event. Format: `EXP-NNN`.
2. **Expert telegram_username**: Stored without `@` prefix. Matched case-insensitively.
3. **Assignment status transitions**: Enforced in service layer (not DB constraints).
4. **One assignment per expert per clustering run**: DB unique constraint.
5. **Reminder count**: Must not exceed 4 (total messages per DD cycle, enforced in service).
6. **Room minimum**: 2 confirmed experts per room = "covered". Service checks this.

## Migration Notes

- Migration depends on: `001_initial_schema` (users, events), `002_projects_clustering` (tags, rooms, clustering_runs)
- Creates 4 tables: experts → expert_tags → expert_room_assignments → escalations
- No data migration needed (seed loaded at runtime)
- Rollback: drop all 4 tables in reverse order
