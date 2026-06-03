from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class SupportMessage(Base):
    """Mirror of backend support_messages (ADR-001: unified support).

    sender_type is one of "user" | "organizer" | "bot".
    """

    __tablename__ = "support_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("support_threads.id"), index=True
    )
    sender_type: Mapped[str] = mapped_column(String(20))
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    # Real column is timestamptz (migration 034); declare tz-aware so values
    # round-trip as offset-aware and never clash with aware datetimes.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    thread = relationship("SupportThread", back_populates="messages")
