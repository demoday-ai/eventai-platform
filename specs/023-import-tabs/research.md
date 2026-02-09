# Research: Import Data Tabs

## R1: Event Creation Endpoint

**Decision**: Add POST `/admin/events` endpoint for explicit event creation.
**Rationale**: Currently events are created implicitly during project upload. The Event tab needs explicit create capability.
**Alternatives**: Reuse PATCH endpoint with upsert logic — rejected because PATCH requires existing event (returns 404).

## R2: shadcn/ui Tabs Component

**Decision**: Copy shadcn Tabs component via CLI or manual copy from radix-ui/react-tabs.
**Rationale**: Project already uses shadcn/ui pattern (manual component copies in `components/ui/`).
**Alternatives**: Custom tabs — rejected (shadcn already used throughout project).

## R3: State Preservation Across Tabs

**Decision**: Keep all tab content mounted (not lazy), preserve existing localStorage persistence for upload results.
**Rationale**: shadcn Tabs renders all TabsContent by default. Existing DataImport already uses localStorage for result persistence. No changes needed.
**Alternatives**: Lazy tab loading — rejected (tabs are lightweight, all content should persist).

## R4: Event Form Duplication vs Extraction

**Decision**: Extract event form logic into shared component or duplicate minimally in DataImport. Settings.tsx keeps its own copy.
**Rationale**: Settings and Import have different contexts — Settings shows event alongside tags/organizers/audit, Import shows event as first step of data pipeline. Shared component adds unnecessary coupling.
**Alternatives**: Shared EventForm component — acceptable but over-engineering for 2 consumers with different contexts.
