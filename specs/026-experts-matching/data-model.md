# Data Model: Experts Matching

No new entities required. All data models already exist in the backend.

## Existing Entities Used

- **Expert**: name, telegram_username, position, tags, assignment_status
- **MatchingResult**: clustering_run_id, total_experts, matched_experts, unmatched_experts, rooms[]
- **Room (in matching)**: room_id, room_name, expert_count, experts[]
- **CoverageSummary**: rooms[], totals (confirmed, pending, declined, coverage_percent)
- **CoverageGap**: room_id, room_name, uncovered_tag, project_count_with_tag, candidates[]
- **Escalation**: id, type, expert_name, room_name, message, resolved, created_at
