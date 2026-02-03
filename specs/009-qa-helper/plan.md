# Implementation Plan: Q&A Helper (EPIC-009)

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
| LLM | OpenRouter API (via llm_client) | Existing service |
| Database | PostgreSQL 16 | Existing |
| Cache | In-memory (dict + TTL) | Simple, no Redis needed |

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Telegram Bot                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  /questions  │  │   /compare   │  │ Inline Callbacks │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
│         └─────────────────┼────────────────────┘            │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     qa_service.py                            │
│  ┌────────────────────┐  ┌────────────────────────────────┐ │
│  │ generate_questions │  │ generate_comparison_matrix     │ │
│  │ get_cached_qa      │  │ add_custom_criterion           │ │
│  └─────────┬──────────┘  └─────────────────┬──────────────┘ │
│            │                               │                 │
│            └───────────────┬───────────────┘                 │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
         ┌───────────────────┴───────────────────┐
         │                                       │
         ▼                                       ▼
┌─────────────────┐                   ┌──────────────────┐
│   llm_client    │                   │   qa_suggestion  │
│  (OpenRouter)   │                   │     (model)      │
└─────────────────┘                   └──────────────────┘
```

### Data Flow

1. User → `/questions` → qa_handler → qa_service
2. qa_service checks cache (QASuggestion, expires_at > now)
3. If miss: qa_service → llm_client → OpenRouter
4. LLM response parsed → saved to QASuggestion
5. Questions returned to user

---

## File Structure

```
backend/
├── alembic/versions/
│   └── 009_qa_suggestion.py          # Migration
├── app/
│   ├── models/
│   │   └── qa_suggestion.py          # QASuggestion model
│   ├── services/
│   │   └── qa_service.py             # Q&A logic + LLM prompts
│   └── bot/handlers/
│       └── qa.py                     # /questions, /compare handlers
```

---

## Database Changes

### New Table: qa_suggestions

```sql
CREATE TABLE qa_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    question_type VARCHAR(50) NOT NULL,
    questions JSONB NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_qa_suggestions_user_project ON qa_suggestions(user_id, project_id);
CREATE INDEX ix_qa_suggestions_expires ON qa_suggestions(expires_at);
```

### Question Types Enum

```python
class QuestionType(str, Enum):
    GUEST_GENERAL = "guest_general"
    GUEST_APPLICANT = "guest_applicant"
    GUEST_PRACTITIONER = "guest_practitioner"
    BUSINESS_INVESTOR = "business_investor"
    BUSINESS_HR = "business_hr"
    BUSINESS_PARTNER = "business_partner"
    BUSINESS_TECH = "business_tech"
```

---

## LLM Prompts

### Guest Questions Prompt

```
You are a Q&A helper for Demo Day. Generate 3-5 questions for a guest visiting project "{project_title}".

Guest profile:
- Type: {guest_subtype} (Applicant/AI-Practitioner/Other)
- Interests: {interests}

Project:
- Title: {project_title}
- Description: {project_description}
- Tech stack: {tech_stack}

Generate questions appropriate for the guest type:
- Applicant: focus on learning, team experience, technologies to study
- AI-Practitioner: focus on architecture, approaches, metrics, reproducibility
- Other: general questions about value and applicability

Output JSON array of strings: ["question1", "question2", ...]
```

### Business Questions Prompt

```
You are a Q&A helper for Demo Day business partners. Generate 3-5 business-focused questions for project "{project_title}".

Partner profile:
- Objective: {objective} (Investment/Hiring/Technology/Partnership)
- Industry: {industry}
- Focus: {focus_areas}

Project:
- Title: {project_title}
- Description: {project_description}
- Tech stack: {tech_stack}

Generate questions based on objective:
- Investment: unit economics, market, team, funding stage
- Hiring: tech stack, experience level, work readiness
- Technology: integration, API, scalability, licensing
- Partnership: business model, pilot readiness, terms

Output JSON array of strings: ["question1", "question2", ...]
```

---

## API Integration

### Existing Endpoints Used

- `GET /api/v1/recommendations/{user_id}` — get user's project recommendations
- `GET /api/v1/projects/{id}` — get project details
- `GET /api/v1/profiles/{user_id}` — get user profile

### New Internal Functions

- `qa_service.generate_questions(user_id, project_id)` → list[str]
- `qa_service.get_comparison_matrix(user_id, project_ids)` → dict
- `qa_service.add_criterion(user_id, criterion)` → updated matrix

---

## Bot Commands

### /questions
- Check user role (guest/business only)
- Fetch recommendations for user
- Show project list with inline buttons
- On project select: generate/fetch questions
- Display questions with "More" / "Back" buttons

### /compare
- Show projects from recommendations
- Multi-select up to 5 projects
- Generate comparison matrix
- Display as formatted text table
- "Add criterion" button → text input → regenerate

---

## Error Handling

| Error | Action |
|-------|--------|
| No recommendations | Suggest /profile first |
| LLM timeout (5s) | Retry once, then show generic questions |
| LLM rate limit | Use cached questions or fallback |
| Invalid project | Show error, return to list |

---

## Testing Strategy

- Unit tests for qa_service functions
- Mock LLM responses for deterministic tests
- Integration test: full flow guest → questions
- Load test: 50 concurrent requests

---

## Dependencies

- EPIC-005/006 must be complete (profiling exists)
- OpenRouter API key configured
- Projects have descriptions (seeded or uploaded)
