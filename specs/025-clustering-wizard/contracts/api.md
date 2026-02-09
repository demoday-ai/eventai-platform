# API Contracts: Clustering Wizard

## Existing Endpoints (No Changes)

All required endpoints already exist:

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/clustering/run | Start clustering job |
| GET | /api/v1/clustering/job/{id} | Poll job status |
| GET | /api/v1/clustering/current | Get current clustering result |
| POST | /api/v1/clustering/{id}/move | Move project between rooms |
| POST | /api/v1/clustering/{id}/approve | Approve clustering |

## No New Endpoints Required

This epic is frontend-only. All backend API is complete.
