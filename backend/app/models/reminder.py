"""Reminder models for EPIC-007: DD Reminders.

Entities:
- ReminderBatch: Tracks a single reminder broadcast operation
- Notification: Individual reminder delivery record
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReminderType(str, enum.Enum):
    """Type of reminder based on timing."""

    DAY_BEFORE = "day_before"
    HOUR_BEFORE = "hour_before"


class ReminderBatchStatus(str, enum.Enum):
    """Status of a reminder batch operation."""

    PREVIEW = "preview"  # Batch created, showing preview
    CONFIRMED = "confirmed"  # Organizer confirmed, ready to send
    IN_PROGRESS = "in_progress"  # Currently sending
    COMPLETED = "completed"  # All notifications processed
    CANCELLED = "cancelled"  # Organizer cancelled


class NotificationStatus(str, enum.Enum):
    """Status of an individual notification."""

    PENDING = "pending"  # Created, not yet sent
    SENT = "sent"  # Successfully delivered
    FAILED = "failed"  # Delivery failed
    SKIPPED = "skipped"  # Skipped (e.g., empty message)


class RecipientType(str, enum.Enum):
    """Type of reminder recipient."""

    STUDENT = "student"
    EXPERT = "expert"
    GUEST = "guest"
    BUSINESS = "business"


class ReminderBatch(Base):
    """Tracks a single reminder broadcast operation."""

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
        DateTime(timezone=True), nullable=False, server_default=func.now()
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
    notifications: Mapped[list["ReminderNotification"]] = relationship(
        "ReminderNotification", back_populates="batch", cascade="all, delete-orphan"
    )


class ReminderNotification(Base):
    """Individual reminder delivery record."""

    __tablename__ = "reminder_notifications"

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
    batch: Mapped["ReminderBatch"] = relationship(
        "ReminderBatch", back_populates="notifications"
    )
    user = relationship("User")
    expert = relationship("Expert")
    participation = relationship("ParticipationRequest")
