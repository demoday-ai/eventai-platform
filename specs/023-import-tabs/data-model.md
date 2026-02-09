# Data Model: Import Data Tabs

## Existing Entities (no changes)

### Event
| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, auto-generated |
| name | String(200) | NOT NULL |
| start_date | Date | NOT NULL |
| end_date | Date | NOT NULL, >= start_date |
| description | Text | nullable |

## New Schemas

### EventCreateRequest (backend)
| Field | Type | Constraints |
|-------|------|-------------|
| name | string | required, min 1 char |
| start_date | date | required |
| end_date | date | required, >= start_date |
| description | string | optional |

### Response: EventResponse (existing, reused)
| Field | Type |
|-------|------|
| id | UUID |
| name | string |
| start_date | date |
| end_date | date |
| description | string or null |

## No New Tables
No database migrations required. Event table already exists.
