# Data Model: Business Partner Profiling

**Date**: 2026-02-02
**Feature**: EPIC-006 (002-business-profiling)

---

## New Entities

### BusinessProfile

Stores the partner's business intent and criteria for project matching.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto | Unique identifier |
| user_id | UUID | FK → users.id, NOT NULL | Partner's user record |
| event_id | UUID | FK → events.id, NOT NULL | Demo Day event |
| objective | Enum | NOT NULL | Investment, Hiring, Technology, Partnership |
| industries | TEXT[] | nullable | List of industry preferences |
| tech_stack | TEXT[] | nullable | List of technology preferences |
| project_stages | TEXT[] | nullable | Preferred stages: idea, mvp, early_traction, scaling, mature |
| collaboration_format | TEXT | nullable | Free text: desired partnership type |
| free_text_raw | TEXT | nullable | Original free-text input (if provided) |
| free_text_parsed | JSONB | nullable | LLM-extracted structured data from free text |
| created_at | TIMESTAMP | NOT NULL, auto | Creation time |
| updated_at | TIMESTAMP | NOT NULL, auto | Last modification time |

**Constraints**:
- UNIQUE(user_id, event_id) — one active profile per partner per event

**Enum: BusinessObjective**:
```python
class BusinessObjective(str, Enum):
    INVESTMENT = "investment"
    HIRING = "hiring"
    TECHNOLOGY = "technology"
    PARTNERSHIP = "partnership"
```

---

### ProjectRecommendation

Stores ranked project matches for a business profile.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto | Unique identifier |
| profile_id | UUID | FK → business_profiles.id, NOT NULL | Associated profile |
| project_id | UUID | FK → projects.id, NOT NULL | Recommended project |
| relevance_score | INTEGER | NOT NULL, 0-100 | Match score |
| relevance_explanation | TEXT | nullable | AI-generated explanation |
| rank | INTEGER | NOT NULL | Position in recommendation list |
| is_bookmarked | BOOLEAN | NOT NULL, default FALSE | User saved this project |
| is_viewed | BOOLEAN | NOT NULL, default FALSE | User viewed details |
| created_at | TIMESTAMP | NOT NULL, auto | When recommendation was generated |

**Constraints**:
- UNIQUE(profile_id, project_id) — no duplicate recommendations
- INDEX on (profile_id, rank) for sorted retrieval

---

## Entity Relationships

```
┌──────────────┐     ┌─────────────────────┐     ┌─────────────┐
│    User      │────<│  BusinessProfile    │>────│   Event     │
└──────────────┘  1:1└─────────────────────┘ N:1 └─────────────┘
                              │
                              │ 1:N
                              ▼
                    ┌─────────────────────────┐
                    │ ProjectRecommendation   │
                    └─────────────────────────┘
                              │
                              │ N:1
                              ▼
                    ┌─────────────────────────┐
                    │       Project           │
                    └─────────────────────────┘
                              │
                              │ N:M (via ProjectTag)
                              ▼
                    ┌─────────────────────────┐
                    │         Tag             │
                    └─────────────────────────┘
```

---

## State Transitions

### BusinessProfile Lifecycle

```
[No Profile] ──(start profiling)──> [Draft]
     │                                  │
     │                                  │ (complete all steps)
     │                                  ▼
     │                              [Pending Confirmation]
     │                                  │
     │         ┌────────────────────────┼────────────────────────┐
     │         │                        │                        │
     │    (confirm)              (edit fields)              (restart)
     │         │                        │                        │
     │         ▼                        ▼                        │
     │     [Active] ◄──────────── [Editing] ──────────────────────┘
     │         │
     │    (modify profile)
     │         │
     └─────────┴──> [Active] (updated_at changes, recommendations regenerated)
```

**Notes**:
- States are implicit (no status column needed)
- "Draft" = profile record exists but not confirmed (no recommendations yet)
- "Active" = confirmed, has recommendations
- "Editing" = user requested changes, show current values

---

## Alembic Migration

**Migration 003**: `003_business_profiles.py`

```python
def upgrade():
    # Enum type
    op.execute("""
        CREATE TYPE business_objective AS ENUM
        ('investment', 'hiring', 'technology', 'partnership')
    """)

    # business_profiles table
    op.create_table(
        'business_profiles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('objective', sa.Enum('investment', 'hiring', 'technology', 'partnership', name='business_objective'), nullable=False),
        sa.Column('industries', ARRAY(sa.Text), nullable=True),
        sa.Column('tech_stack', ARRAY(sa.Text), nullable=True),
        sa.Column('project_stages', ARRAY(sa.Text), nullable=True),
        sa.Column('collaboration_format', sa.Text, nullable=True),
        sa.Column('free_text_raw', sa.Text, nullable=True),
        sa.Column('free_text_parsed', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'event_id', name='uq_business_profiles_user_event'),
    )

    # project_recommendations table
    op.create_table(
        'project_recommendations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('profile_id', UUID(as_uuid=True), sa.ForeignKey('business_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relevance_score', sa.Integer, nullable=False),
        sa.Column('relevance_explanation', sa.Text, nullable=True),
        sa.Column('rank', sa.Integer, nullable=False),
        sa.Column('is_bookmarked', sa.Boolean, nullable=False, default=False),
        sa.Column('is_viewed', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('profile_id', 'project_id', name='uq_recommendations_profile_project'),
    )
    op.create_index('ix_recommendations_profile_rank', 'project_recommendations', ['profile_id', 'rank'])

def downgrade():
    op.drop_table('project_recommendations')
    op.drop_table('business_profiles')
    op.execute('DROP TYPE business_objective')
```

---

## Validation Rules

### BusinessProfile

| Field | Validation |
|-------|------------|
| objective | Required, must be valid enum value |
| industries | Max 10 items, each max 100 chars |
| tech_stack | Max 15 items, each max 50 chars |
| project_stages | Must be subset of allowed values |
| free_text_raw | Max 2000 chars |

### ProjectRecommendation

| Field | Validation |
|-------|------------|
| relevance_score | 0-100 inclusive |
| rank | 1-based, consecutive within profile |
