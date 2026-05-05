from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base

# 031-bot-replacement: enum is named user_role_code in demoday schema (migration 037).
# create_type=False because the enum is created by alembic, not by this model.
role_enum = Enum("guest", "business", "expert", name="user_role_code", create_type=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    telegram_user_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255), default=None)
    role_code: Mapped[str | None] = mapped_column(role_enum, default=None)
    subrole: Mapped[str | None] = mapped_column(String(128), default=None)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
