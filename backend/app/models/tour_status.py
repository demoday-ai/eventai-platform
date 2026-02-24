"""Admin tour completion tracking model."""

import uuid
from datetime import datetime, timezone
from typing import ClassVar

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AdminTourStatus(Base):
    """Tracks which organizers have completed the admin tour.

    Uses telegram_id as primary key instead of the standard UUID id from Base.
    The id column from Base is explicitly excluded via ClassVar to avoid mapping
    a column that does not exist in the database table.
    """

    __tablename__ = "admin_tour_status"

    # Exclude the inherited UUID id from Base — this table uses telegram_id as PK.
    id: ClassVar[uuid.UUID]  # type: ignore[assignment]

    telegram_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    prompted_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
