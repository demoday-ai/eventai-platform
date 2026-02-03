# Implementation Plan: Student Feedback (EPIC-012)

**Version:** 1.0
**Date:** 2026-02-03
**Spec:** [spec.md](./spec.md)

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12+ / FastAPI |
| Bot | python-telegram-bot 21.x |
| LLM | OpenRouter API |
| Database | PostgreSQL 16 |

---

## File Structure

```
backend/
├── alembic/versions/
│   └── 012_feedback_comment.py
├── app/
│   ├── models/
│   │   └── feedback_comment.py
│   ├── services/
│   │   └── feedback_service.py
│   └── bot/handlers/
│       └── feedback.py
```

---

## Database Schema

```sql
CREATE TABLE feedback_comments (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id),
    expert_id UUID NOT NULL REFERENCES experts(id),
    original_text TEXT NOT NULL,
    processed_text TEXT,
    category VARCHAR(20),
    is_constructive BOOLEAN DEFAULT TRUE,
    moderation_status VARCHAR(20) DEFAULT 'pending',
    moderator_notes TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## LLM Prompts

### Feedback Processing Prompt
```
Analyze this feedback comment from an expert about a student project.

Comment: "{comment}"

Tasks:
1. Determine if constructive (true/false)
2. Extract key points (bullet list)
3. Categorize: technical, product, presentation, or general
4. Rewrite in constructive tone (if needed)

Output JSON:
{
  "is_constructive": true/false,
  "category": "...",
  "key_points": ["...", "..."],
  "processed_text": "..."
}
```

---

## Bot Commands

### /feedback (organizer only)
- Show projects with pending feedback
- Select project → show feedback list
- For each: original + processed + actions

### Callbacks
- `fb:proj:{id}` — select project
- `fb:approve:{id}` — approve feedback
- `fb:reject:{id}` — reject feedback
- `fb:edit:{id}` — edit mode
- `fb:send:{project_id}` — send all approved to student
