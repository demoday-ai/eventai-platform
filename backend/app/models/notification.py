"""Notification model - tracks all messages sent to participants."""
import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NotificationType(str, Enum):
    EVE_OF_DD = "eve_of_dd"
    PRE_SLOT = "pre_slot"
    TIMING_SHIFT = "timing_shift"
    PROGRAM_CANCELLED = "program_cancelled"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BATCHED = "batched"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_event_id", "event_id"),
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_type", "type"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_scheduled_at", "scheduled_at"),
        # Partial unique index for deduplication (created in migration as raw SQL)
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    schedule_slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schedule_slots.id", ondelete="SET NULL"),
        nullable=True,
    )

    type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NotificationStatus.PENDING.value
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reminder_day: Mapped[date | None] = mapped_column(Date, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    user = relationship("User")
    event = relationship("Event")
    schedule_slot = relationship("ScheduleSlot", back_populates="notifications")
