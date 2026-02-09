# API Contracts: Audience Segmentation

No new backend endpoints needed. All filtering is client-side.

## Existing endpoint used:

```
GET /api/v1/admin/guests
Query: search?, subtype?, role?
Response: GuestListItem[]
```

## Navigation contract (frontend):

```
Link to: /messaging?segment_role=business&segment_tags=NLP,CV
```

Messaging page reads URL search params and pre-selects recipients.
