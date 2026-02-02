# Quickstart: Загрузка и AI-кластеризация проектов

**Branch**: `002-project-clustering`

## Prerequisites

- EPIC-001 (Onboarding) merged to main
- PostgreSQL 16 running
- Python 3.12+
- `.env` с переменными из EPIC-001 + новые:

```env
# Existing (EPIC-001)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/demoday
BOT_TOKEN=<telegram-bot-token>
SECRET_KEY=<jwt-secret>
ORGANIZER_TELEGRAM_IDS=<comma-separated>

# New (EPIC-002)
OPENROUTER_API_KEY=<api-key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-4.1
```

## Setup

```bash
# 1. Checkout branch
git checkout 002-project-clustering

# 2. Install dependencies (if new ones added)
cd backend
pip install -r requirements.txt  # or pip install -e .

# 3. Run migration
alembic upgrade head

# 4. Prepare seed data (one-time)
cd ..
python scripts/prepare_seed.py

# 5. Start the app
cd backend
uvicorn app.main:app --reload
```

## Demo Flow

1. Open Telegram bot
2. `/start` → choose "Организатор" role
3. Bot shows wizard: "Загружено 305 проектов (демо-данные). Запустить кластеризацию?"
4. Press "Запустить кластеризацию"
5. Set number of rooms (default 6), confirm
6. Wait for clustering result (~30-60 sec)
7. Browse rooms, view projects
8. Optional: move a project, re-cluster with feedback
9. "Утвердить расписание"

## API Testing

```bash
# Upload projects (replace with your token)
curl -X POST http://localhost:8000/api/v1/projects/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test_projects.csv"

# Run clustering
curl -X POST http://localhost:8000/api/v1/clustering/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"num_rooms": 6}'

# Get current result
curl http://localhost:8000/api/v1/clustering/current \
  -H "Authorization: Bearer <token>"

# Move project
curl -X POST http://localhost:8000/api/v1/clustering/<run_id>/move \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "<uuid>", "target_room_id": "<uuid>"}'

# Approve
curl -X POST http://localhost:8000/api/v1/clustering/<run_id>/approve \
  -H "Authorization: Bearer <token>"
```

## Test Data

- **Seed**: `data/seed/projects_seed.json` (~305 projects from checkpoint forms)
- **Manual upload**: Create a CSV with columns: `title,description,tags,author,telegram_contact`

Example CSV:
```csv
title,description,tags,author,telegram_contact
AI StudyPath Mentor,Персональный маршрут обучения,"NLP,EdTech,Agents",Студент_001,@user_001
Turbo Sorter,AI-система сортировки документов,"NLP,Security",Студент_002,@user_002
```
