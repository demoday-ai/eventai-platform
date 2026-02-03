# Implementation Plan: Organizer Dashboard (EPIC-011)

**Version:** 1.0
**Date:** 2026-02-03
**Spec:** [spec.md](./spec.md)

---

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Backend | Python 3.12+ / FastAPI | Existing stack |
| Bot | python-telegram-bot 21.x | Existing |
| ORM | SQLAlchemy 2.0 async | Existing |
| Database | PostgreSQL 16 | Existing |

---

## Architecture

### Component Diagram

```
┌───────────────────────────────────────────────────────────┐
│                     Telegram Bot                          │
│  ┌─────────────────┐  ┌─────────────────────────────────┐│
│  │   /dashboard    │  │   dash:* callbacks              ││
│  └────────┬────────┘  └────────────────┬────────────────┘│
│           │                            │                  │
└───────────┼────────────────────────────┼──────────────────┘
            │                            │
            ▼                            ▼
┌───────────────────────────────────────────────────────────┐
│                  dashboard_service.py                     │
│  ┌───────────────────┐  ┌─────────────────────────────┐  │
│  │ get_student_stats │  │ get_expert_stats            │  │
│  │ get_guest_stats   │  │ get_alerts                  │  │
│  │ format_dashboard  │  │ get_no_show_list            │  │
│  └───────────────────┘  └─────────────────────────────┘  │
│                                                           │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
  ┌─────────────────┐            ┌─────────────────┐
  │ participation_  │            │ expert_room_    │
  │   request       │            │   assignment    │
  └─────────────────┘            └─────────────────┘
```

---

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   └── dashboard_service.py      # Dashboard stats logic
│   └── bot/handlers/
│       └── dashboard.py              # /dashboard handler
```

---

## Database Queries

### Student Stats
```sql
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed,
    COUNT(*) FILTER (WHERE status = 'confirmed' AND checkin_at IS NOT NULL) as checked_in,
    COUNT(*) FILTER (WHERE status = 'declined') as declined
FROM participation_requests
WHERE event_id = :event_id
```

### Expert Stats
```sql
SELECT
    COUNT(*) as total_invited,
    COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed,
    COUNT(DISTINCT room_id) FILTER (WHERE status = 'confirmed') as rooms_covered
FROM expert_room_assignments
WHERE clustering_run_id = :clustering_run_id
```

### Guest Stats
```sql
SELECT
    guest_subtype,
    COUNT(*) as count
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
WHERE ur.event_id = :event_id
  AND ur.role_id = (SELECT id FROM roles WHERE code = 'guest')
GROUP BY guest_subtype
```

### Business Partner Count
```sql
SELECT COUNT(*) FROM business_profiles
WHERE user_id IN (
    SELECT user_id FROM user_roles WHERE event_id = :event_id
)
```

---

## Bot Handler

### /dashboard
1. Check organizer role
2. Fetch all stats via dashboard_service
3. Generate alerts based on thresholds
4. Format and send message
5. Add action buttons

### Callbacks
- `dash:refresh` — reload dashboard
- `dash:noshows` — show no-show students list
- `dash:problems` — show problematic rooms
- `dash:guests` — show guest breakdown

---

## Alert Thresholds

| Alert | Condition | Level |
|-------|-----------|-------|
| No expert in room | room.expert_count == 0 | CRITICAL |
| High no-show rate | no_shows > 20% of confirmed | CRITICAL |
| Low confirmation | confirmed < 70% of total | WARNING |
| Slot starting soon | slot in 30 min, not confirmed | WARNING |

---

## Testing Strategy

- Unit tests for dashboard_service stats functions
- Integration test with test data
- Test alert generation logic
