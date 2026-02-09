# Data Model: Audience Segmentation

No new database entities needed. All data is already available in the Guest model.

## Existing entities used:

- **GuestListItem**: id, full_name, username, role, guest_subtype, tags[], keywords[], profile_summary, recommendations_count, contact_requests_count, has_business_profile, created_at
- **Filter State** (client-side only): selectedTags: string[], activityFilter: string ("has_recommendations" | "has_business_profile" | "has_contacts" | ""), search: string, roleFilter: string
