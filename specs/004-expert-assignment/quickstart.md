# Quickstart: Распределение экспертов (EPIC-004)

## Prerequisites

- EPIC-001 (Onboarding) deployed and running
- EPIC-002 (Project Clustering) deployed with at least one **approved** clustering run
- PostgreSQL 16 running with migrations applied
- `.env` configured with `BOT_TOKEN`, `OPENROUTER_API_KEY`, `ORGANIZER_TELEGRAM_IDS`

## Setup

### 1. Apply migration

```bash
cd backend
alembic upgrade head
```

This creates 4 new tables: `experts`, `expert_tags`, `expert_room_assignments`, `escalations`.

### 2. Prepare expert seed data

```bash
python scripts/prepare_expert_seed.py
```

Merges `data/expert-mapping.json` + `data/experts-public.json` → `data/seed/experts_seed.json` (294 experts with tags).

### 3. Start the application

```bash
cd backend
python -m app.main
```

On startup, the app loads `experts_seed.json` into DB if no experts exist for the current event.

## Demo Flow

### Step 1: Verify prerequisites

Open Telegram bot as organizer. Check that a clustering run is approved:
- Use `/clustering` command → should show an approved run with rooms

### Step 2: Run expert matching

As organizer in bot:
1. Send `/experts` → bot shows expert management menu
2. Tap **"Запустить матчинг"**
3. Bot runs tag-overlap matching with adjacent tag resolution via LLM
4. Bot shows result: per-room expert counts with match scores

### Step 3: Review and adjust

1. Tap a room to see assigned experts with scores
2. To move an expert: tap expert → **"Перенести"** → select target room
3. Repeat until satisfied

### Step 4: Approve distribution

1. Tap **"Утвердить распределение"**
2. Bot asks for confirmation
3. Confirm → all assignments move to "approved" status

### Step 5: Send invites (two-step)

1. Tap **"Отправить приглашения"**
2. Bot shows preview: N experts, sample message, link for group chat
3. Confirm → assignments move to "invite_ready"
4. Bot provides link: `t.me/botname?start=expert`
5. Share this link in the expert group chat

### Step 6: Expert responds

When expert opens the bot via link:
1. Bot recognizes by Telegram username
2. Shows personalized invite: "Приглашаем на DD! По вашим интересам (NLP, Agents) подходит Зал 3. 25 проектов."
3. Expert taps **"Иду"** / **"Хочу другую комнату"** / **"Не смогу"**

### Step 7: Monitor coverage

As organizer:
1. Send `/coverage` → bot shows coverage dashboard
2. Each room: confirmed/needed count, color indicator
3. Tap room for drill-down: expert list with statuses

### Step 8: Handle escalations

- After 3 days: experts in bot who didn't respond get a reminder
- After 5 days (or 2 days before DD): organizer gets escalation alert
- Organizer can resolve escalations via `/escalations` command

## API Verification

```bash
# List experts
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/experts

# Run matching
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/matching/run

# Get coverage
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/coverage
```

## Key Numbers (from real DD data)

| Metric | Value |
|--------|-------|
| Total experts in seed | 294 |
| Experts with tags | ~208 (71%) |
| Experts without tags | ~86 (29%) |
| Unique tags | 31 |
| Rooms (typical) | 6-10 |
| Min experts per room | 2 |
| Experts with "Придет" status | ~76 |
| Telegram contacts available | ~280 |
