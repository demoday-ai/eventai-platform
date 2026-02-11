"""Admin tour completion tracking model."""

from datetime import datetime, timezone

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AdminTourStatus(Base):
    """Tracks which organizers have completed the admin tour."""

    __tablename__ = "admin_tour_status"

    telegram_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    prompted_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
