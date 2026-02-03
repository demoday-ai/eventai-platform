# Quickstart: Business Partner Profiling

**Feature**: EPIC-006 (002-business-profiling)
**Prerequisites**: EPIC-001 (onboarding), EPIC-002 (projects) must be deployed

---

## 1. Run Migration

```bash
cd backend
alembic upgrade head
```

This creates:
- `business_profiles` table
- `project_recommendations` table
- `business_objective` enum type

---

## 2. Verify Dependencies

```bash
# Check projects are seeded (from EPIC-002)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM projects;"
# Expected: ~400 projects

# Check tags exist
psql $DATABASE_URL -c "SELECT COUNT(*) FROM tags;"
# Expected: ~30 tags
```

---

## 3. Start the Bot

```bash
cd backend
python -m app.main
```

---

## 4. Test Profiling Flow

1. Open Telegram, find your bot
2. Send `/start`
3. Select "Бизнес/партнёр" role
4. Complete profiling:
   - Choose objective (e.g., "Инвестиции")
   - Select industries (e.g., "FinTech", "NLP")
   - Select project stages (e.g., "MVP", "Early traction")
   - Optionally add free-text description
   - Confirm profile
5. View recommendations (5 projects per page)
6. Tap "Подробнее" to see project details

---

## 5. API Testing

```bash
# Create profile via API
curl -X POST http://localhost:8000/api/v1/profiles/business \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<user-uuid>",
    "event_id": "<event-uuid>",
    "objective": "investment",
    "industries": ["fintech", "nlp"],
    "project_stages": ["mvp", "early_traction"]
  }'

# Get recommendations
curl http://localhost:8000/api/v1/profiles/business/<profile-id>/recommendations?page=1

# Extract profile from text
curl -X POST http://localhost:8000/api/v1/profiles/business/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Ищу NLP-проекты на стадии MVP для инвестиций в EdTech"
  }'
```

---

## 6. Verify Success Criteria

| Criterion | How to Verify |
|-----------|---------------|
| SC-001: Profiling ≤2 min | Time the flow from objective selection to confirmation |
| SC-005: Relevant project in top-5 | Check if at least one project matches stated interests |
| SC-006: Recommendations <5 sec | Measure time from confirmation to recommendations display |

---

## Troubleshooting

### "AI-сервис временно недоступен"

LLM API is unreachable. Check:
```bash
# Verify OpenRouter config
echo $OPENROUTER_API_KEY
echo $OPENROUTER_BASE_URL

# Test LLM directly
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "openai/gpt-4.1", "messages": [{"role": "user", "content": "test"}]}'
```

### No recommendations generated

1. Check projects exist: `SELECT COUNT(*) FROM projects WHERE event_id = '<event-id>';`
2. Check tags match profile criteria
3. Check profile was saved: `SELECT * FROM business_profiles WHERE user_id = '<user-id>';`

### Callback data error

Telegram callback_data exceeds 64 bytes. Check:
- Project UUIDs are truncated to 8 chars in callbacks
- No multi-select with too many items
