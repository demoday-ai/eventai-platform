from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class BusinessFollowup(Base):
    __tablename__ = "business_followups"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"))
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String(64), default="interested")
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    # NOTE: real table (migration 038) has loi_generated and NO updated_at —
    # declaring updated_at here caused UndefinedColumnError on SELECT.
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
