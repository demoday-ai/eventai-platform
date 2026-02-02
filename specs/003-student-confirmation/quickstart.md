# Quickstart: EPIC-003 Student Schedule Acknowledgment

## Prerequisites

- EPIC-001 (onboarding) merged and running
- EPIC-002 (clustering) merged — projects loaded, clustering done, schedule approved
- PostgreSQL running with existing schema (migrations 001-004)
- Bot running in polling mode

## Integration Scenarios

### Scenario 1: Organizer broadcasts schedule

```
1. Organizer sends /broadcast command in bot
2. System checks: approved ClusteringRun exists for current event
3. For each project in approved rooms:
   a. Match project.telegram_contact → user.username → user.telegram_user_id
   b. Create ParticipationRequest (status=pending)
   c. Send Telegram message: "Ты выступаешь {date}, {room_name}, слот #{order}"
   d. Update status → sent, save telegram_message_id
   e. Sleep 0.04s (rate limiting)
4. Report to organizer: "Отправлено: X. Неподключённых: Y" + list
```

### Scenario 2: Student acknowledges

```
1. Student receives message with inline button "Ознакомлен"
2. Student presses button → callback_data = "ack:{request_id[:8]}"
3. Bot handler:
   a. Find ParticipationRequest by short UUID prefix
   b. Verify request belongs to this user
   c. Set status = acknowledged, acknowledged_at = now()
   d. Answer callback: "Отлично! Напоминание придёт за день до выступления"
```

### Scenario 3: Automatic reminder (DD-5d)

```
1. Periodic task runs every hour
2. Query: status=sent AND reminder_sent_at IS NULL AND event.start_date - now() <= 5 days
3. For each match:
   a. Send reminder: "Напоминаем: ты выступаешь {date}, {room}, слот #{order}. Нажми Ознакомлен."
   b. Set reminder_sent_at = now()
```

### Scenario 4: Escalation to organizer (DD-2d)

```
1. Periodic task runs every hour
2. Query: status=sent AND escalated_at IS NULL AND event.start_date - now() <= 2 days
3. Collect all unacknowledged students
4. Send to each organizer: "N студентов не ознакомились с расписанием:" + list
5. Set escalated_at = now() for each
```

### Scenario 5: Re-broadcast after schedule change

```
1. Organizer changes clustering (moves projects between rooms)
2. Organizer sends /broadcast again
3. For each project:
   a. If no ParticipationRequest exists → create and send (new student)
   b. If exists AND room_project_id unchanged → skip
   c. If exists AND room_project_id changed → update, reset status=sent,
      clear acknowledged_at, send new message with "Расписание изменено" prefix
```

### Scenario 6: Organizer checks dashboard

```
1. Organizer sends /status command
2. Bot shows summary: "Ознакомились: X/Y. Не ответили: Z"
3. Per-room breakdown with inline buttons for filtering
4. Can drill down: show list of unacknowledged students per room
```

## Key Commands (Bot)

| Command | Role | Description |
|---------|------|-------------|
| /broadcast | Organizer | Запустить рассылку слотов |
| /status | Organizer | Сводка ознакомлений |

## Key Endpoints (REST API)

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/participation/broadcast | Запустить рассылку |
| GET | /api/v1/participation/summary | Сводка по статусам |
| GET | /api/v1/participation/unacknowledged | Список неознакомленных |

## Test Data Setup

```python
# Create event with start_date = today + 10 days
# Load projects via seed_service (existing)
# Run clustering (existing)
# Approve clustering
# → Ready for /broadcast
```
