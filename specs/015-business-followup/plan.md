# Implementation Plan: Business Follow-up (EPIC-015)

**Version:** 1.0
**Date:** 2026-02-03

## File Structure

```
backend/
├── alembic/versions/
│   └── 015_business_followup.py
├── app/
│   ├── models/
│   │   └── business_followup.py
│   ├── services/
│   │   └── business_followup_service.py
│   └── bot/handlers/
│       └── business_followup.py
```

## Bot Flow

1. /bizfollowup → show business-specific package
2. Select project → view details, change status
3. Request LOI → generate personalized letter template
4. Track pipeline via inline buttons

## Commands

- /bizfollowup — business partner follow-up package
- /loi {project} — generate LOI for specific project

## Callbacks

- bf:proj:{id} — view project details
- bf:status:{id}:{status} — update pipeline status
- bf:loi:{id} — generate LOI
- bf:notes:{id} — add notes

## Integration Points

- EPIC-005: BusinessProfile for objectives
- EPIC-010: ContactRequest for approved contacts
- EPIC-014: Base follow-up functionality
