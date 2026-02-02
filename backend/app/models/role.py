import enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RoleCode(str, enum.Enum):
    ORGANIZER = "organizer"
    STUDENT = "student"
    EXPERT = "expert"
    GUEST = "guest"
    BUSINESS = "business"


ROLE_DISPLAY_NAMES = {
    RoleCode.ORGANIZER: "Организатор",
    RoleCode.STUDENT: "Студент",
    RoleCode.EXPERT: "Эксперт",
    RoleCode.GUEST: "Гость",
    RoleCode.BUSINESS: "Бизнес-партнёр",
}


class Role(Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
