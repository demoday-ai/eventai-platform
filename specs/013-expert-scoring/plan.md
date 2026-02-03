# Implementation Plan: Expert Scoring (EPIC-013)

**Version:** 1.0
**Date:** 2026-02-03

## File Structure

```
backend/
├── alembic/versions/
│   └── 013_expert_score.py
├── app/
│   ├── models/
│   │   └── expert_score.py
│   ├── services/
│   │   └── scoring_service.py
│   └── bot/handlers/
│       └── scoring.py
```

## Bot Flow

1. After slot ends → notify expert with score prompt
2. Expert selects scores via inline buttons (1-3 per criterion)
3. Overall impression (1-5)
4. Optional comment
5. Submit → create ExpertScore + FeedbackComment

## Commands

- /score — show unscored projects for expert
- Callbacks: score:* for rating flow
