# API Contracts: Experts Matching

## Existing Endpoints (No Changes)

All required endpoints already exist:

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/matching/run | Run expert matching |
| GET | /api/v1/matching/current | Get current matching result |
| POST | /api/v1/matching/move | Move expert between rooms |
| POST | /api/v1/matching/assign | Assign expert to room |
| POST | /api/v1/matching/approve | Approve matching |
| GET | /api/v1/matching/invite-preview | Get invite preview |
| POST | /api/v1/matching/confirm-invites | Confirm and send invites |
| GET | /api/v1/experts | List all experts |
| POST | /api/v1/experts | Create expert |
| PUT | /api/v1/experts/:id | Update expert |
| PATCH | /api/v1/experts/:id/status | Update expert status |
| GET | /api/v1/coverage/summary | Get coverage summary |
| GET | /api/v1/coverage/gaps | Get coverage gaps |
| GET | /api/v1/coverage/rooms/:id | Get room coverage detail |
| GET | /api/v1/escalations | Get escalations |
| POST | /api/v1/escalations/:id/resolve | Resolve escalation |

## No New Endpoints Required

This epic is frontend-only. All backend API is complete.
