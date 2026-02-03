# Research: EPIC-006 — Organizer Coverage Dashboard

## R1: Existing Coverage Implementation

**Decision**: Extend existing coverage functions, don't replace them.

**Context**: EPIC-004 already has `invite_service.get_coverage_dashboard()` and `get_room_coverage_detail()` with REST endpoints `GET /coverage` and `GET /coverage/{room_id}`. These return expert counts and statuses per room.

**What exists**:
- `get_coverage_dashboard`: room-level expert counts (confirmed/declined/no_response), coverage_level (covered/partial/uncovered)
- `get_room_coverage_detail`: per-room expert list with tags, match_score, status + suggested adjacent experts from other rooms

**What's missing for EPIC-006**:
- Project counts per room (not returned currently)
- Project tags per room (top themes)
- Tag-based gap analysis (project tags with no expert match)
- Free expert recommendations for gaps (currently only suggests experts from other rooms)
- Telegram bot command `/coverage` (no bot interface at all)

**Approach**: Create `coverage_service.py` with enriched functions that call or replace the existing ones. Update API endpoints to use new service. Add bot handler.

**Alternatives rejected**:
- Modifying invite_service directly — it's already large (450+ lines) and focused on write operations (invites, reminders, escalations). Coverage is read-only.

## R2: Tag-Based Gap Analysis Algorithm

**Decision**: Exact tag name match between project_tags and expert_tags.

**Rationale**: Both use the same `tags` table. A project tag "NLP" matches expert tag "NLP" by identical `tag_id`. No fuzzy matching or hierarchy needed.

**Algorithm**:
1. For each room, collect project tags: `SELECT DISTINCT t.name FROM project_tags pt JOIN tags t ... WHERE project_id IN (room's projects)`
2. For each room, collect expert tags (where status=confirmed): `SELECT DISTINCT t.name FROM expert_tags et JOIN tags t ... WHERE expert_id IN (confirmed experts in room)`
3. Gap = project_tags - expert_tags (set difference)
4. For each gap tag, find free experts with that tag not assigned to this room

**Alternatives rejected**:
- LLM-based semantic matching — YAGNI, tags are already curated and shared
- Partial/fuzzy matching — adds complexity without clear benefit given shared tag vocabulary

## R3: "Free Expert" Definition for Recommendations

**Decision**: An expert who has the matching tag and is NOT already assigned to the target room (regardless of other room assignments).

**Rationale**: Experts can be assigned to multiple rooms. An expert in Room 1 can still be recommended for Room 3 if they have a matching tag. The organizer decides whether to add them.

**Alternative rejected**: Only recommending unassigned experts — too restrictive, most experts are already assigned somewhere.

## R4: Telegram Message Format for Coverage Summary

**Decision**: Text-based summary with emoji indicators + inline keyboard for drill-down.

**Format**:
```
📊 Покрытие залов

✅ Зал «NLP/Agents»: 3/2 эксп. | 45 проектов
⚠️ Зал «FinTech»: 1/2 эксп. | 38 проектов
❌ Зал «CV/ML»: 0/2 эксп. | 52 проектов
...

Итого: 8/12 подтверждено (67%)
```

Inline buttons per room for drill-down. Refresh button at bottom.

**Constraints**: 4096 char Telegram message limit. With ~10 rooms at ~50 chars each = ~500 chars. Well within limit.

## R5: Bot Command Name

**Decision**: `/coverage` — new command, doesn't conflict with existing commands (`/start`, `/broadcast`, `/status`, `/cluster`).

**Rationale**: Clear, descriptive. Organizer-only (same pattern as `/broadcast` and `/status`).

## R6: Service Architecture

**Decision**: New `coverage_service.py` with pure read-only functions.

**Functions**:
1. `get_coverage_summary(session, event_id)` → enriched room list with project counts + tags
2. `get_room_detail(session, event_id, room_id)` → experts + projects + gap analysis
3. `get_coverage_gaps(session, event_id)` → all uncovered tags across all rooms + candidates
4. `find_expert_candidates(session, tag_name, exclude_room_id)` → free experts for a gap

**Existing endpoints** (`GET /coverage`, `GET /coverage/{room_id}`) will be updated to call new service functions for richer data. Backward-compatible — adds fields, doesn't remove any.

## R7: No New Database Models

**Decision**: No new tables or migrations needed.

**Rationale**: All data exists in:
- `rooms` + `room_projects` → project counts per room
- `project_tags` + `tags` → project themes
- `expert_room_assignments` → expert coverage status
- `expert_tags` + `tags` → expert competencies

Coverage is pure aggregation over existing data. No state to persist.
