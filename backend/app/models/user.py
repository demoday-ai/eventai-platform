import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GuestSubtype(str, enum.Enum):
    APPLICANT = "applicant"
    AI_PRACTITIONER = "ai_practitioner"
    OTHER = "other"


GUEST_SUBTYPE_DISPLAY = {
    GuestSubtype.APPLICANT: "Абитуриент",
    GuestSubtype.AI_PRACTITIONER: "AI-практик",
    GuestSubtype.OTHER: "Другое",
}


class User(Base):
    __tablename__ = "users"

    telegram_user_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    guest_subtype: Mapped[GuestSubtype | None] = mapped_column(
        Enum(GuestSubtype, name="guest_subtype_enum"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
