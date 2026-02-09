# Data Model: Clustering Wizard

## Existing Entities (No Changes Needed)

### ClusteringRun
- id (UUID, PK)
- status (String: pending/running/completed/failed)
- num_rooms (Integer)
- feedback (Text, nullable)
- created_at (DateTime)
- approved_at (DateTime, nullable)

### Room
- id (UUID, PK)
- name (String)
- theme_rationale (Text)
- clustering_run_id (FK → ClusteringRun)

### Project
- id (UUID, PK)
- title (String)
- description (Text)
- author (String)
- tags (via project_tags junction)
- room_id (FK → Room, nullable)

## No New Entities Required

All data model needs are covered by existing entities. This epic is frontend-only enhancement.
