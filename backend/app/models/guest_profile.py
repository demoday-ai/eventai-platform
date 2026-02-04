import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GuestProfile(Base):
    __tablename__ = "guest_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_guest_profiles_user_event"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    extracted_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    recommendations = relationship(
        "Recommendation",
        back_populates="guest_profile",
        cascade="all, delete-orphan",
    )
