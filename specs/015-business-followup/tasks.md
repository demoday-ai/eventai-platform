# Tasks: Business Follow-up (EPIC-015)

**Version:** 1.0
**Date:** 2026-02-03

## Phase 1: Database & Model

- [X] Create BusinessFollowup model with PipelineStatus enum (backend/app/models/business_followup.py)
- [X] Create Alembic migration (backend/alembic/versions/015_business_followup.py)
- [X] Export model in __init__.py

## Phase 2: Service Layer

- [X] Create business_followup_service.py with functions:
  - get_business_profile()
  - get_pipeline_projects()
  - add_to_pipeline()
  - update_status()
  - add_notes()
  - generate_loi()
  - format_pipeline_message()
  - init_pipeline_from_recommendations()
- [X] LOI templates by BusinessObjective

## Phase 3: Bot Handlers

- [X] Create business_followup.py handlers:
  - /bizfollowup command
  - project_detail_callback
  - status_callback
  - loi_callback
  - notes_callback + receive_notes
  - back_callback, refresh_callback
- [X] Register handlers in app.py

## Phase 4: Testing

- [ ] Test /bizfollowup with business profile
- [ ] Verify pipeline initialization from recommendations
- [ ] Test status updates
- [ ] Test LOI generation with different objectives
- [ ] Test notes functionality
