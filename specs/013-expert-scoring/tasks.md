# Tasks: Expert Scoring (EPIC-013)

**Version:** 1.0
**Date:** 2026-02-03

## Phase 1: Database & Model

- [X] Create ExpertScore model (backend/app/models/expert_score.py)
- [X] Create Alembic migration (backend/alembic/versions/013_expert_score.py)
- [X] Export model in __init__.py

## Phase 2: Service Layer

- [X] Create scoring_service.py with functions:
  - get_expert_by_telegram()
  - get_projects_to_score()
  - create_or_update_score()
  - add_comment_to_score()
  - get_expert_scores_summary()
  - format_score_criteria()

## Phase 3: Bot Handlers

- [X] Create scoring.py handlers:
  - /score command
  - project_select_callback
  - criterion_callback (6 criteria, 1-3 each)
  - overall_callback (1-5)
  - skip_callback
  - comment_callback + receive_comment
  - done_callback
- [X] Register handlers in app.py

## Phase 4: Testing

- [ ] Test /score flow with expert
- [ ] Verify score persistence
- [ ] Test skip functionality
- [ ] Test comment addition via EPIC-012 integration
