# Quickstart: Empty States и подсказки

**Feature**: 021-empty-states

## Prerequisites

- Node.js 18+
- Frontend dependencies installed: `cd frontend && npm install`

## Verify

1. Start the frontend dev server:
   ```bash
   cd frontend && npm run dev
   ```

2. Open the admin panel (no event in database):
   - Navigate to Dashboard → should show existing "Нет активного мероприятия" empty state
   - Navigate to Projects → should show "Проекты ещё не загружены" + link to Import
   - Navigate to Clustering → should show "Для кластеризации необходимы проекты" + link to Import
   - Navigate to Experts → should show "Для матчинга необходима одобренная кластеризация" + link
   - Navigate to Schedule → should show "Для генерации расписания необходима одобренная кластеризация" + link
   - Navigate to Messaging → should show "Создайте мероприятие" + link to Import
   - Navigate to Audience → should show "Создайте мероприятие" + link to Import

3. Run tests:
   ```bash
   cd frontend && npx vitest run
   ```

## Validation Checklist

- [ ] All 6 pages show empty states when prerequisites missing
- [ ] Empty states have consistent visual style (dashed border, icon, text, button)
- [ ] Navigation is never blocked
- [ ] Empty states disappear when data is loaded (auto-refresh)
- [ ] All tests pass
