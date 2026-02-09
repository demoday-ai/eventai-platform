# Implementation Plan: Audience Segmentation

**Branch**: `030-audience-segments`
**Spec**: `specs/030-audience-segments/spec.md`

## Technical Context

- GuestList.tsx (325 lines) already has search + role filter
- Need to add: tag multi-select filter, activity filters, "Send to segment" button
- All data already available from GET /admin/guests endpoint
- No new backend endpoints needed
- Frontend-only changes

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Telegram-First | N/A | Admin panel feature, not bot |
| II. AI-Augmented, Human-Approved | PASS | No AI involvement in filtering |
| III. Data-Driven | PASS | Uses existing guest data |
| IV. Pragmatic Development | PASS | Minimal code, YAGNI (no saved segments in DB) |

## Phase 0: Research → research.md ✅
## Phase 1: Design → data-model.md, contracts/api.md ✅

## Phase 2: Implementation

### Scope

1. Add tag filter (multi-select chips from available tags in guest pool)
2. Add activity filter (has recommendations, has business profile, has contacts)
3. Add "Send to segment" button that navigates to /messaging with filter params
4. Add active filter count + reset button
5. Client-side filtering logic
6. Tests for new filter functionality
