# Data Model: Напоминания перед Demo Day (EPIC-007)

**Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Entity Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      EPIC-007 Entities                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   Event                                                      │
│     │                                                        │
│     ├──< ReminderBatch (1:N)                                 │
│     │      │                                                 │
│     │      └──< Notification (1:N)                           │
│     │             │                                          │
│     │             ├── → User (guest/business)                │
│     │             ├── → Expert                               │
│     │             └── → ParticipationRequest (student)       │
│     │                                                        │
│     ├──< ParticipationRequest (existing, EPIC-003)           │
│     │      └── → User, Project, RoomProject                  │
│     │                                                        │
│     └──< ExpertRoomAssignment (existing, EPIC-004)           │
│            └── → Expert, Room                                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## New Entities

### ReminderBatch

Tracks a single reminder broadcast operation.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| event_id | UUID | FK → events.id, NOT NULL | Target event |
| reminder_type | Enum | NOT NULL | `day_before` \| `hour_before` |
| initiated_by | String(20) | NOT NULL | Telegram user_id of organizer |
| initiated_by_name | String(200) | NULL | Organizer display name |
| total_recipients | Integer | NOT NULL, DEFAULT 0 | Expected recipients |
| sent_count | Integer | NOT NULL, DEFAULT 0 | Successfully sent |
| failed_count | Integer | NOT NULL, DEFAULT 0 | Failed to send |
| skipped_count | Integer | NOT NULL, DEFAULT 0 | Skipped (no Telegram) |
| started_at | DateTime | NOT NULL | When batch started |
| completed_at | DateTime | NULL | When batch completed |
| status | Enum | NOT NULL | `preview` \| `confirmed` \| `in_progress` \| `completed` \| `cancelled` |
| created_at | DateTime | NOT NULL | Auto timestamp |

**Indexes**:
- `ix_reminder_batches_event_id` on `event_id`
- `ix_reminder_batches_status` on `status`
- `ix_reminder_batches_reminder_type_started_at` on `(reminder_type, started_at)` — for duplicate detection

### Notification

Individual reminder delivery record.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| batch_id | UUID | FK → reminder_batches.id, NOT NULL | Parent batch |
| recipient_type | Enum | NOT NULL | `student` \| `expert` \| `guest` \| `business` |
| telegram_user_id | String(20) | NOT NULL | Recipient's Telegram user ID |
| user_id | UUID | FK → users.id, NULL | For guests/business |
| expert_id | UUID | FK → experts.id, NULL | For experts |
| participation_id | UUID | FK → participation_requests.id, NULL | For students |
| status | Enum | NOT NULL, DEFAULT 'pending' | `pending` \| `sent` \| `failed` |
| error_message | String(500) | NULL | Error details if failed |
| message_text | Text | NULL | Actual message sent (for audit) |
| sent_at | DateTime | NULL | When successfully sent |
| created_at | DateTime | NOT NULL | Auto timestamp |

**Indexes**:
- `ix_notifications_batch_id` on `batch_id`
- `ix_notifications_status` on `status`
- `ix_notifications_telegram_user_id` on `telegram_user_id`

**Constraints**:
- CHECK: At least one of `user_id`, `expert_id`, `participation_id` must be NOT NULL

## Extended Entities

### Expert (add field)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| telegram_chat_id | String(20) | NULL, INDEX | Telegram chat ID for messaging (set on bot_started) |

**Migration**: Add nullable column, populated when expert starts bot.

## Enum Definitions

### ReminderType

```python
class ReminderType(str, enum.Enum):
    DAY_BEFORE = "day_before"
    HOUR_BEFORE = "hour_before"
```

### ReminderBatchStatus

```python
class ReminderBatchStatus(str, enum.Enum):
    PREVIEW = "preview"         # Batch created, showing preview
    CONFIRMED = "confirmed"     # Organizer confirmed, ready to send
    IN_PROGRESS = "in_progress" # Currently sending
    COMPLETED = "completed"     # All notifications processed
    CANCELLED = "cancelled"     # Organizer cancelled
```

### NotificationStatus

```python
class NotificationStatus(str, enum.Enum):
    PENDING = "pending"   # Created, not yet sent
    SENT = "sent"         # Successfully delivered
    FAILED = "failed"     # Delivery failed
```

### RecipientType

```python
class RecipientType(str, enum.Enum):
    STUDENT = "student"
    EXPERT = "expert"
    GUEST = "guest"
    BUSINESS = "business"
```

## SQLAlchemy Models

### reminder.py

```python
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReminderType(str, enum.Enum):
    DAY_BEFORE = "day_before"
    HOUR_BEFORE = "hour_before"


class ReminderBatchStatus(str, enum.Enum):
    PREVIEW = "preview"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class RecipientType(str, enum.Enum):
    STUDENT = "student"
    EXPERT = "expert"
    GUEST = "guest"
    BUSINESS = "business"


class ReminderBatch(Base):
    __tablename__ = "reminder_batches"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reminder_type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType, name="reminder_type_enum"),
        nullable=False,
    )
    initiated_by: Mapped[str] = mapped_column(String(20), nullable=False)
    initiated_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    total_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[ReminderBatchStatus] = mapped_column(
        Enum(ReminderBatchStatus, name="reminder_batch_status_enum"),
        nullable=False,
        default=ReminderBatchStatus.PREVIEW,
        index=True,
    )

    # Relationships
    event = relationship("Event")
    notifications = relationship(
        "Notification", back_populates="batch", cascade="all, delete-orphan"
    )


class Notification(Base):
    __tablename__ = "notifications"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reminder_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_type: Mapped[RecipientType] = mapped_column(
        Enum(RecipientType, name="recipient_type_enum"),
        nullable=False,
    )
    telegram_user_id: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experts.id", ondelete="SET NULL"),
        nullable=True,
    )
    participation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participation_requests.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status_enum"),
        nullable=False,
        default=NotificationStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    batch = relationship("ReminderBatch", back_populates="notifications")
    user = relationship("User")
    expert = relationship("Expert")
    participation = relationship("ParticipationRequest")
```

## Migration Script Outline

```python
"""Add reminder tables for EPIC-007.

Revision ID: xxx
Revises: yyy
Create Date: 2026-02-03
"""

def upgrade():
    # Create enums
    op.execute("CREATE TYPE reminder_type_enum AS ENUM ('day_before', 'hour_before')")
    op.execute("CREATE TYPE reminder_batch_status_enum AS ENUM ('preview', 'confirmed', 'in_progress', 'completed', 'cancelled')")
    op.execute("CREATE TYPE notification_status_enum AS ENUM ('pending', 'sent', 'failed')")
    op.execute("CREATE TYPE recipient_type_enum AS ENUM ('student', 'expert', 'guest', 'business')")

    # Create reminder_batches table
    op.create_table(
        'reminder_batches',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reminder_type', sa.Enum('day_before', 'hour_before', name='reminder_type_enum'), nullable=False),
        sa.Column('initiated_by', sa.String(20), nullable=False),
        sa.Column('initiated_by_name', sa.String(200), nullable=True),
        sa.Column('total_recipients', sa.Integer, default=0, nullable=False),
        sa.Column('sent_count', sa.Integer, default=0, nullable=False),
        sa.Column('failed_count', sa.Integer, default=0, nullable=False),
        sa.Column('skipped_count', sa.Integer, default=0, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('preview', 'confirmed', 'in_progress', 'completed', 'cancelled', name='reminder_batch_status_enum'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_reminder_batches_event_id', 'reminder_batches', ['event_id'])
    op.create_index('ix_reminder_batches_status', 'reminder_batches', ['status'])

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('batch_id', UUID(as_uuid=True), sa.ForeignKey('reminder_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_type', sa.Enum('student', 'expert', 'guest', 'business', name='recipient_type_enum'), nullable=False),
        sa.Column('telegram_user_id', sa.String(20), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('expert_id', UUID(as_uuid=True), sa.ForeignKey('experts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('participation_id', UUID(as_uuid=True), sa.ForeignKey('participation_requests.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('pending', 'sent', 'failed', name='notification_status_enum'), nullable=False),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('message_text', sa.Text, nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_notifications_batch_id', 'notifications', ['batch_id'])
    op.create_index('ix_notifications_status', 'notifications', ['status'])
    op.create_index('ix_notifications_telegram_user_id', 'notifications', ['telegram_user_id'])

    # Add telegram_chat_id to experts
    op.add_column('experts', sa.Column('telegram_chat_id', sa.String(20), nullable=True))
    op.create_index('ix_experts_telegram_chat_id', 'experts', ['telegram_chat_id'])


def downgrade():
    op.drop_index('ix_experts_telegram_chat_id', 'experts')
    op.drop_column('experts', 'telegram_chat_id')

    op.drop_table('notifications')
    op.drop_table('reminder_batches')

    op.execute('DROP TYPE notification_status_enum')
    op.execute('DROP TYPE recipient_type_enum')
    op.execute('DROP TYPE reminder_batch_status_enum')
    op.execute('DROP TYPE reminder_type_enum')
```

## Query Patterns

### Get recipients for day-before reminders

```python
# Students with slots
students = await session.execute(
    select(ParticipationRequest)
    .where(ParticipationRequest.event_id == event_id)
    .where(ParticipationRequest.room_project_id.isnot(None))
    .where(ParticipationRequest.user_id.isnot(None))
    .options(
        joinedload(ParticipationRequest.user),
        joinedload(ParticipationRequest.project),
        joinedload(ParticipationRequest.room_project).joinedload(RoomProject.room),
    )
)

# Experts (not declined)
experts = await session.execute(
    select(ExpertRoomAssignment)
    .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
    .where(ExpertRoomAssignment.status != "declined")
    .options(
        selectinload(ExpertRoomAssignment.expert),
        selectinload(ExpertRoomAssignment.room),
    )
)

# Guests with program
guests = await session.execute(
    select(User)
    .where(User.guest_subtype.isnot(None))
    # join with GuestProgram if exists
)
```

### Check for duplicate batch

```python
recent_batch = await session.execute(
    select(ReminderBatch)
    .where(ReminderBatch.event_id == event_id)
    .where(ReminderBatch.reminder_type == reminder_type)
    .where(ReminderBatch.status == ReminderBatchStatus.COMPLETED)
    .where(ReminderBatch.started_at > datetime.now(timezone.utc) - timedelta(hours=24))
    .order_by(ReminderBatch.started_at.desc())
    .limit(1)
)
```
