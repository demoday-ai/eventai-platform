# Feature Specification: Audience Segmentation

**Feature Branch**: `030-audience-segments`
**Created**: 2026-02-09
**Status**: Draft
**Input**: EPIC-010 (US-032 gap: advanced filters, saved segments, send to segment)

## Existing Implementation

GuestList.tsx (325 lines) already covers US-030 (table), US-031 (detail panel), US-041 (empty states). Only US-032 (segmentation) has gaps.

## User Scenarios & Testing

### User Story 1 - Advanced Audience Filters (Priority: P1)

As an organizer, I want to filter guests by tags/interests and activity level so I can find specific audience segments for targeted communication.

**Why this priority**: Core filtering is the foundation for all segmentation features. Without it, organizers cannot identify specific audience groups.

**Independent Test**: Can be tested by applying tag and activity filters and verifying the guest table updates accordingly.

**Acceptance Scenarios**:

1. **Given** guests with various tags, **When** organizer selects tag filter "NLP", **Then** only guests with NLP in their tags or interests are shown
2. **Given** guests with varying activity, **When** organizer filters by "has recommendations", **Then** only guests with recommendations_count > 0 are shown
3. **Given** multiple filters applied, **When** organizer clicks "Reset filters", **Then** all filters are cleared and full list is shown

---

### User Story 2 - Send Broadcast to Filtered Segment (Priority: P2)

As an organizer, I want to send a broadcast to the currently filtered audience segment so I can communicate with specific groups without manual selection.

**Why this priority**: Direct integration with messaging enables actionable use of filters. This is the main business value of segmentation.

**Independent Test**: Can be tested by filtering guests, clicking "Send to segment", and verifying navigation to messaging page with pre-applied filters.

**Acceptance Scenarios**:

1. **Given** guests filtered by role "business", **When** organizer clicks "Send to segment", **Then** navigate to /messaging with role=business pre-selected
2. **Given** no filters applied, **When** looking at the page, **Then** "Send to segment" button is not shown (send all guests from messaging page instead)

---

### Edge Cases

- What happens when filters result in zero guests? Show "No guests match filters" message.
- What happens when guest has no tags/interests? They are excluded from tag-based filters but visible with no filters applied.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide filter by tags (multi-select from available tags in the guest pool)
- **FR-002**: System MUST provide filter by activity: "has recommendations", "has business profile", "has contact requests"
- **FR-003**: System MUST show active filter count and provide a "Reset" button to clear all filters
- **FR-004**: System MUST show a "Send to segment" button when filters are active, navigating to /messaging with current filter parameters
- **FR-005**: All filters MUST be applied client-side on the already-loaded guest list (no new backend endpoints needed)
- **FR-006**: System MUST display the count of filtered guests prominently

### Key Entities

- **Guest**: Existing entity with tags, keywords, recommendations_count, contact_requests_count, has_business_profile
- **Filter State**: Client-side state: selectedTags, activityFilters, roleFilter, search

## Success Criteria

### Measurable Outcomes

- **SC-001**: Organizer can narrow down audience using tag and activity filters in under 10 seconds
- **SC-002**: Filtered guest count is always visible and accurate
- **SC-003**: "Send to segment" navigates to messaging with correct pre-selected parameters
- **SC-004**: All existing functionality (table, detail panel, empty states) continues working unchanged

## Assumptions

- Backend already returns all needed guest data (tags, keywords, recommendations_count, has_business_profile)
- Saved segments (US-032 AC: "Сохранение сегмента для повторного использования") are deferred to Release 1.1 as they require backend persistence and are not in the minimal viable feature set
- Tag filter options are derived from the tags present in the current guest list
