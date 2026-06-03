from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class SupportThread(Base):
    """Mirror of backend support_threads (ADR-001: unified support).

    One open thread per user per event. The web admin (SupportChat.tsx)
    reads/writes the same table; the bot creates threads + user messages here.
    """

    __tablename__ = "support_threads"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    closed_by: Mapped[str | None] = mapped_column(String(20), default=None)
    needs_attention: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # Real column is timestamptz (migration 034); declare tz-aware to match
    # updated_at and avoid naive/aware comparison errors.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages = relationship(
        "SupportMessage",
        back_populates="thread",
        order_by="SupportMessage.created_at",
    )
