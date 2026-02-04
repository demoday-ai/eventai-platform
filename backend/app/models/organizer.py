"""Organizer model for DB-based access management."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Organizer(Base):
    __tablename__ = "organizers"

    telegram_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
