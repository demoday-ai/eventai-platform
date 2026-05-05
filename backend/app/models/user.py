import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GuestSubtype(str, enum.Enum):
    STUDENT = "student"
    APPLICANT = "applicant"
    OTHER = "other"
    INVESTOR = "investor"
    BUSINESS_PARTNER = "business_partner"
    MENTOR = "mentor"
    HR = "hr"
    JURY = "jury"


GUEST_SUBTYPE_DISPLAY = {
    GuestSubtype.STUDENT: "🎓 Студент",
    GuestSubtype.APPLICANT: "📚 Абитуриент",
    GuestSubtype.OTHER: "Другое — ввести текстом",
    GuestSubtype.INVESTOR: "💰 Инвестор",
    GuestSubtype.BUSINESS_PARTNER: "🤝 Бизнес-партнёр",
    GuestSubtype.MENTOR: "🧑‍🏫 Ментор",
    GuestSubtype.HR: "👔 HR",
    GuestSubtype.JURY: "⚖️ Жюри",
}


class UserRoleCode(str, enum.Enum):
    """Role coarse classification used by bonus-track-llm bot agent.

    Maps from GuestSubtype (8 values) to 3 coarse buckets:
      student | applicant | other         -> guest
      investor | business_partner | hr     -> business
      mentor | jury                        -> expert
    """

    GUEST = "guest"
    BUSINESS = "business"
    EXPERT = "expert"


GUEST_SUBTYPE_TO_ROLE_CODE: dict[GuestSubtype, UserRoleCode] = {
    GuestSubtype.STUDENT: UserRoleCode.GUEST,
    GuestSubtype.APPLICANT: UserRoleCode.GUEST,
    GuestSubtype.OTHER: UserRoleCode.GUEST,
    GuestSubtype.INVESTOR: UserRoleCode.BUSINESS,
    GuestSubtype.BUSINESS_PARTNER: UserRoleCode.BUSINESS,
    GuestSubtype.HR: UserRoleCode.BUSINESS,
    GuestSubtype.MENTOR: UserRoleCode.EXPERT,
    GuestSubtype.JURY: UserRoleCode.EXPERT,
}


class User(Base):
    __tablename__ = "users"

    telegram_user_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    guest_subtype: Mapped[GuestSubtype | None] = mapped_column(
        Enum(GuestSubtype, name="guest_subtype_enum"), nullable=True
    )
    role_code: Mapped[UserRoleCode | None] = mapped_column(
        Enum(UserRoleCode, name="user_role_code"), nullable=True
    )
    subrole: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str | None] = mapped_column(String(10), nullable=True, server_default="bot")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
