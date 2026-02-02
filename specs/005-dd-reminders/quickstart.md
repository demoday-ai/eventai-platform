# Quickstart: DD Reminders & Timing Shift Notifications (EPIC-005)

## Prerequisites

- EPIC-001 (Onboarding) deployed and running
- EPIC-002 (Project Clustering) deployed with at least one **approved** clustering run
- EPIC-004 (Expert Assignment) deployed (for escalation infrastructure)
- PostgreSQL 16 running with migrations 001-003 applied
- `.env` configured with `BOT_TOKEN`, `ORGANIZER_TELEGRAM_IDS`

## Setup

### 1. Apply migration

```bash
cd backend
alembic upgrade head
```

This creates 3 new tables: `schedule_slots`, `notifications`, `schedule_change_logs`.

### 2. Start the application

```bash
cd backend
python -m app.main
```

On startup, APScheduler registers the new jobs:
- Eve-of-DD reminder (CronTrigger: 18:00 MSK, day before each event day)
- Pre-slot checker (IntervalTrigger: every 5 min, active on DD day only)
- Notification batch processor (IntervalTrigger: every 60 sec)

## Demo Flow

### Step 1: Verify prerequisites

Open Telegram bot as organizer. Confirm:
- `/clustering` shows an approved run with rooms and projects
- At least some users exist (students, experts, guests)

### Step 2: Generate schedule

As organizer in bot:
1. Send `/schedule` → bot shows schedule menu
2. Tap **"Сгенерировать расписание"**
3. Bot auto-generates slots from approved clustering:
   - Each project → 15-min slot in its assigned room
   - Slots ordered sequentially within each room
   - Day 1 (10:30-19:30) and Day 2 (14:00-19:30) time windows
4. Bot shows summary: "Расписание сгенерировано: N слотов, M залов, K дней"

### Step 3: Review and adjust schedule

1. Tap a room to see its timeline
2. To move a project: tap slot → **"Перенести"** → select new time or room
3. To cancel a project: tap slot → **"Отменить"**
4. Bot shows updated schedule after each change

### Step 4: Approve schedule

1. Tap **"Утвердить расписание"**
2. Bot confirms: "Расписание утверждено. Напоминания будут отправлены автоматически."

### Step 5: Preview reminders (optional)

1. Tap **"Превью напоминаний"**
2. Bot shows: recipient count by role, sample message per role
3. Buttons: **"Подтвердить"** / **"Отменить рассылку"**

### Step 6: Automatic eve-of-DD reminders

At 18:00 MSK the day before Demo Day:
- Organizer receives preview at 17:00 MSK with cancel option
- If not cancelled by 18:00, reminders are sent automatically
- Students: room + time + "Удачи!"
- Experts: room + time + project list
- Guests/Business: personal program (or generic message if no profiling)

### Step 7: Day-of pre-slot reminders

On DD day, every 5 minutes the system checks for slots starting in ~1 hour:
- Students get: "Через час — твоё выступление!"
- Experts get: "Через час — начало оценки!"
- Guests/Business get: "Через час — [top project]!"
- No duplicates (tracked in notifications table)

### Step 8: Timing shift notifications

If organizer changes schedule during DD:
1. Use `/schedule` → tap slot → **"Перенести"**
2. System automatically queues timing shift notifications
3. Affected participants receive: "Проект X перенесён: было 14:00 → стало 16:00"
4. If multiple changes within 5 min, notifications are batched

### Step 9: Monitor delivery

As organizer:
1. Tap **"Дашборд доставки"** in `/schedule` menu
2. See: total sent/failed/pending by role
3. See: list of unreachable participants (never started bot)
4. Unreachable participants also appear as escalations in `/escalations`

## API Verification

```bash
# Generate schedule
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/schedule/generate

# Get full schedule
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/schedule

# Update a slot (move time)
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"start_time": "2026-02-06T16:00:00+03:00", "end_time": "2026-02-06T16:15:00+03:00"}' \
  http://localhost:8000/api/v1/schedule/slots/{slot_id}

# Preview reminders
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/reminders/preview?day=2026-02-06

# Manually send reminders
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"day": "2026-02-06"}' \
  http://localhost:8000/api/v1/reminders/send

# Get notification dashboard
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/notifications/dashboard
```

## Key Numbers (from real DD data)

| Metric | Value |
|--------|-------|
| Total projects | ~330 |
| Rooms (typical) | 6-10 |
| Slot duration | 15 min |
| Day 1 time window | 10:30-19:30 (9h = 36 slots/room) |
| Day 2 time window | 14:00-19:30 (5.5h = 22 slots/room) |
| Participants to notify | ~400-500 |
| Eve-of-DD send time | ~14 sec (at 30 msg/sec) |
| Timezone | Moscow (UTC+3) |

## Testing Notes

For local testing without waiting for scheduled times:
- Use `/reminders/send` API endpoint to manually trigger reminders
- Set `FORCE_REMINDER_NOW=true` environment variable to bypass time checks
- Use `MOCK_TELEGRAM=true` to log messages instead of sending via Telegram API
