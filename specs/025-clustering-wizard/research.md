# Research: Clustering Wizard

## R1: Current Implementation Gap Analysis

**Decision**: Clustering.tsx (475 lines) already implements ~90% of EPIC-005. Only 3 gaps remain.
**Gaps found**:
1. No confirmation dialog before approve — USM says "Кнопка «Одобрить» с подтверждением"
2. No next-step hint after approval — USM says "Подсказка: «Следующий шаг — распределение экспертов»"
3. No Global Stepper / pipeline-status invalidation after approve

**Rationale**: Minimal changes needed. Add confirm state + hint + queryClient.invalidateQueries for pipeline-status.

## R2: Confirmation Dialog Approach

**Decision**: Use inline confirm state (not a modal dialog) — show "Вы уверены?" with Confirm/Cancel buttons replacing the Approve button.
**Rationale**: Consistent with project patterns (no modal library used). Simpler than adding a dialog component.
**Alternatives**: shadcn AlertDialog — rejected (over-engineering for one button).

## R3: Next-Step Hint

**Decision**: After approval, show a Card with green border containing "Кластеризация одобрена. Следующий шаг — распределение экспертов" with a link to /experts page.
**Rationale**: Matches USM AC and existing pattern of pipeline hints in the project.
