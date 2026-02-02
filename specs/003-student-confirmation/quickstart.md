# Quickstart: EPIC-003 Student Confirmation

## Prerequisites

- EPIC-001 (onboarding) merged and running
- EPIC-002 (clustering) merged — approved ClusteringRun with rooms and projects
- PostgreSQL running with existing schema
- Bot token configured in .env

## Setup

```bash
# 1. Switch to feature branch
git checkout 003-student-confirmation

# 2. Run migration
cd backend
alembic upgrade head

# 3. Start the app
uvicorn app.main:app --reload
```

## Test Flow

### 1. Prepare test data

Ensure you have:
- An approved ClusteringRun (status='done', approved_at set)
- Projects assigned to rooms (room_projects)
- Projects with `telegram_contact` filled

### 2. Trigger broadcast (as organizer)

In Telegram bot, use the organizer command to broadcast slots.
Or via API:

```bash
curl -X POST http://localhost:8000/api/v1/participation/broadcast \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"clustering_run_id": "<uuid>"}'
```

### 3. Confirm as student

In the Telegram bot, tap "Подтверждаю" or "Не смогу" on the received message.

### 4. Check summary (as organizer)

```bash
curl http://localhost:8000/api/v1/participation/summary \
  -H "Authorization: Bearer <token>"
```

## Key Files

| File | Purpose |
|------|---------|
| `app/models/participation.py` | ParticipationRequest model |
| `app/schemas/participation.py` | Pydantic schemas |
| `app/services/participation_service.py` | Business logic: broadcast, confirm, remind, escalate |
| `app/api/participation.py` | REST endpoints for organizer |
| `app/bot/handlers/confirmation.py` | Telegram bot handler for student confirmation |
| `alembic/versions/003_participation_requests.py` | DB migration |
