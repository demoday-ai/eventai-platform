# Research: Audience Segmentation

## Decision: Client-side filtering

**Rationale**: Backend already returns all guest data with tags, keywords, recommendations_count, contact_requests_count, has_business_profile. Guest lists are small (< 500 users) so client-side filtering is fast and avoids new backend endpoints.

**Alternatives considered**:
- Backend filtering with query params — unnecessary, adds complexity for small dataset
- Saved segments in DB — deferred to Release 1.1 per YAGNI (Constitution IV)

## Decision: Tag filter from guest pool

**Rationale**: Extract unique tags from the loaded guest list for the filter dropdown. No separate tags endpoint needed.

## Decision: Navigation to messaging with URL params

**Rationale**: Pass filter state via URL search params (e.g., /messaging?role=business&tags=NLP,CV) to pre-select recipients in the broadcast form. The Messaging page already supports role-based recipient selection.

**Alternative**: React Router state — less shareable, doesn't survive page refresh.
