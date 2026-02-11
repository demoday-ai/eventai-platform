"""Schedule change log model - audit trail for schedule modifications."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ChangeType(str, Enum):
    TIME_CHANGED = "time_changed"
    ROOM_CHANGED = "room_changed"
    TIME_AND_ROOM_CHANGED = "time_and_room_changed"
    CANCELLED = "cancelled"
    RESTORED = "restored"


class ScheduleChangeLog(Base):
    __tablename__ = "schedule_change_logs"
    __table_args__ = (
        Index("ix_schedule_change_logs_slot_id", "schedule_slot_id"),
        Index("ix_schedule_change_logs_event_id", "event_id"),
    )

    schedule_slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schedule_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    change_type: Mapped[str] = mapped_column(String(30), nullable=False)

    old_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    old_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    old_room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True
    )

    new_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    new_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    new_room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True
    )

    notifications_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    schedule_slot = relationship("ScheduleSlot", back_populates="change_logs")
    changed_by = relationship("User")
    old_room = relationship("Room", foreign_keys=[old_room_id])
    new_room = relationship("Room", foreign_keys=[new_room_id])
