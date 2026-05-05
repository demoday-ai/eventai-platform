import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.types import JSONType


class Expert(Base):
    __tablename__ = "experts"
    __table_args__ = (
        UniqueConstraint("seed_id", "event_id", name="uq_experts_seed_event"),
        Index("ix_experts_telegram_username", "telegram_username"),
        Index("ix_experts_seed_id", "seed_id"),
    )

    seed_id: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[str | None] = mapped_column(String(500), nullable=True)
    inviter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dd_status_seed: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dd_comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )

    bot_started: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bot_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # 031-bot-replacement: bonus-track-llm fields
    invite_code: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    tags_json: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    # Single-room reference used by bot expert flow; admin keeps using
    # expert_room_assignment for richer multi-room/coverage logic.
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
    )

    user = relationship("User")
    tags = relationship("ExpertTag", back_populates="expert", cascade="all, delete-orphan")
    assignments = relationship("ExpertRoomAssignment", back_populates="expert", cascade="all, delete-orphan")
