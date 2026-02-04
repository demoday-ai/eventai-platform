import uuid
from datetime import date

from pydantic import BaseModel

from app.models.role import RoleCode
from app.models.user import GuestSubtype


class TelegramAuthRequest(BaseModel):
    telegram_user_id: str
    full_name: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class SetRoleRequest(BaseModel):
    role_code: RoleCode
    guest_subtype: GuestSubtype | None = None


class SetGuestSubtypeRequest(BaseModel):
    guest_subtype: GuestSubtype


class RoleInfo(BaseModel):
    code: RoleCode
    name: str


class UserProfile(BaseModel):
    id: uuid.UUID
    telegram_user_id: str
    full_name: str
    username: str | None = None
    role: RoleInfo | None = None
    guest_subtype: GuestSubtype | None = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    user: UserProfile


class EventResponse(BaseModel):
    id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    description: str | None = None

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    detail: str
