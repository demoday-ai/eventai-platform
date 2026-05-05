from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import JSONType


class Event(Base):
    __tablename__ = "events"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_experts_per_room: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    evaluation_criteria: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Europe/Moscow", server_default="Europe/Moscow"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
