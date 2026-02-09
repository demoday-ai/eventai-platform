# API Contract: Import Data Tabs

## New Endpoint

### POST /api/v1/admin/events
Create a new event.

**Request**:
```json
{
  "name": "Demo Day 2026",
  "start_date": "2026-03-15",
  "end_date": "2026-03-16",
  "description": "Optional description"
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "name": "Demo Day 2026",
  "start_date": "2026-03-15",
  "end_date": "2026-03-16",
  "description": "Optional description"
}
```

**Response 409**: Event already exists
```json
{
  "detail": "Active event already exists"
}
```

**Response 422**: Validation error (end_date < start_date)

## Existing Endpoints (no changes)

### GET /api/v1/events/current
Returns current event or 404.

### PATCH /api/v1/admin/events/current
Updates existing event fields.
