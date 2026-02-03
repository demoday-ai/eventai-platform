# Data Model: EPIC-006 — Organizer Coverage Dashboard

## No New Tables

EPIC-006 is read-only aggregation over existing data. No new models, no migrations.

## Existing Tables Used

### rooms
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| clustering_run_id | UUID | FK → clustering_runs |
| name | str(200) | Room name/theme |
| theme_rationale | text | AI-generated rationale |
| display_order | int | Sort order |

### room_projects
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| room_id | UUID | FK → rooms |
| project_id | UUID | FK → projects |
| is_manual | bool | Manual assignment flag |

### expert_room_assignments
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| expert_id | UUID | FK → experts |
| room_id | UUID | FK → rooms |
| clustering_run_id | UUID | FK → clustering_runs |
| match_score | float | 0.0-1.0 relevance |
| status | str(20) | proposed/approved/invite_ready/invited/confirmed/declined |
| is_manual | bool | Manual assignment flag |

### tags (shared between experts and projects)
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| name | str(100) | Tag name, unique |

### expert_tags
| Field | Type | Notes |
|-------|------|-------|
| expert_id | UUID | FK → experts |
| tag_id | UUID | FK → tags |

### project_tags
| Field | Type | Notes |
|-------|------|-------|
| project_id | UUID | FK → projects |
| tag_id | UUID | FK → tags |

## Aggregation Queries

### Coverage Summary (per room)
```
For each room in approved clustering:
  project_count = COUNT(room_projects WHERE room_id = room.id)
  top_tags = SELECT tag.name, COUNT(*) FROM project_tags
             JOIN room_projects ON ... GROUP BY tag.name ORDER BY count DESC LIMIT 5
  confirmed_experts = COUNT(expert_room_assignments WHERE room_id AND status='confirmed')
  pending_experts = COUNT(... WHERE status IN ('proposed','approved','invite_ready','invited'))
  coverage_level = 'covered' if confirmed >= 2, 'partial' if 1, 'uncovered' if 0
```

### Gap Analysis (per room)
```
project_tag_names = SELECT DISTINCT tag.name FROM project_tags
                    JOIN room_projects ON project_tags.project_id = room_projects.project_id
                    WHERE room_projects.room_id = room.id

expert_tag_names = SELECT DISTINCT tag.name FROM expert_tags
                   JOIN expert_room_assignments ON ...
                   WHERE room_id = room.id AND status = 'confirmed'

uncovered_tags = project_tag_names - expert_tag_names
```

### Expert Candidates (for uncovered tag)
```
SELECT expert.id, expert.name, expert_tags
FROM experts
JOIN expert_tags ON ...
JOIN tags ON tag.name = :uncovered_tag
WHERE expert.id NOT IN (
  SELECT expert_id FROM expert_room_assignments
  WHERE room_id = :target_room_id AND clustering_run_id = :run_id
)
```

## Status Machine (ExpertRoomAssignment.status)

Existing from EPIC-004, no changes:

```
proposed → approved → invite_ready → invited → confirmed
                                             → declined
```

For coverage counting:
- **Confirmed**: status = 'confirmed'
- **Pending**: status IN ('proposed', 'approved', 'invite_ready', 'invited')
- **Declined**: status = 'declined'
