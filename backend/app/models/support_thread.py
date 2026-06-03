from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SupportThread(Base):
    __tablename__ = "support_threads"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    closed_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    needs_attention: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    taken_over: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", lazy="selectin")
    messages = relationship("SupportMessage", back_populates="thread", order_by="SupportMessage.created_at")
