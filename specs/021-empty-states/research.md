# Research: Empty States и подсказки

**Feature**: 021-empty-states
**Date**: 2026-02-09

## Decision 1: Reusable Component vs Per-Page Inline

**Decision**: Create a single reusable `PageEmptyState` component in `components/ui/`.

**Rationale**: All empty states share the same visual pattern (dashed card, icon, title, description, action button). A single component ensures consistency (FR-005) and follows YAGNI (Constitution VII).

**Alternatives considered**:
- Per-page inline JSX: Rejected — duplicates code, inconsistent styling, harder to maintain.
- Extend existing `EmptyState` from dashboard: Rejected — that component is Dashboard-specific with hardcoded text and navigation. Better to create a generic one.

## Decision 2: How to Detect Pipeline Dependencies

**Decision**: Use existing query data on each page (e.g., `getCurrentClustering()` returns 404 or null when no clustering exists). No new API endpoints needed.

**Rationale**: Each page already queries its prerequisite data. Empty state is shown based on the query result (empty array, null, or error). This avoids adding backend complexity.

**Alternatives considered**:
- New `/api/v1/admin/prerequisites` endpoint: Rejected — over-engineering; each page already knows its dependencies.
- Use `usePipelineStatus` hook globally: Rejected — the hook provides phase-level status but not granular enough for per-page checks (e.g., "projects loaded" vs "clustering approved").

## Decision 3: Empty State Hierarchy on Messaging Page

**Decision**: Three-tier check: (1) no event → (2) no participants → (3) show normal UI. The "no broadcasts yet" message is inline in the Overview tab, not a full-page empty state.

**Rationale**: Messaging page has multiple tabs. A full-page empty state would hide the tabs. The tiered approach checks the most critical dependency first (event existence), then secondary (participants).

**Alternatives considered**:
- Full-page empty state replacing all tabs: Rejected — breaks FR-003 (no blocking navigation).
- Single combined message: Rejected — unhelpful; user needs to know specifically what's missing.

## Decision 4: Component Location

**Decision**: `frontend/src/components/ui/PageEmptyState.tsx` — in the `ui/` directory alongside other reusable UI primitives.

**Rationale**: This is a UI primitive (like Button, Card), not a domain-specific component. Follows the project convention where `components/ui/` holds generic, reusable components.

**Alternatives considered**:
- `components/shared/PageEmptyState.tsx`: No `shared/` directory exists in the project.
- `components/dashboard/EmptyState.tsx` (extend): Would tie a generic component to a specific domain folder.

## Existing Code Analysis

### Pages needing empty states:

| Page | File | Current State | Dependency Check |
|------|------|---------------|------------------|
| ProjectsList | `pages/ProjectsList.tsx` | Shows "Нет проектов" text when empty; has `isNoEventError` check | Need: link to Import when 0 projects |
| Clustering | `pages/Clustering.tsx` | Shows wizard step 0 always; no projects check | Need: check if projects exist before showing wizard |
| ExpertMatching | `pages/ExpertMatching.tsx` | Shows "Запуск матчинга" step; mentions "Требуется одобренная кластеризация" in text | Need: full empty state with link if no approved clustering |
| Schedule | `pages/Schedule.tsx` | Shows generation form always; loads clustering data | Need: check if clustering approved before showing wizard |
| Messaging | `pages/Messaging.tsx` | Shows tabs always | Need: tiered empty state (no event → no participants) |
| GuestList | `pages/GuestList.tsx` | Has `isNoEventError` check; shows "Гости не найдены" | Need: informational message when 0 guests (bot-dependent) |

### Existing EmptyState component:
- Location: `components/dashboard/EmptyState.tsx`
- Hardcoded: icon (FolderOpen), title, description, action → `/import`
- Not reusable as-is; needs parameterization
