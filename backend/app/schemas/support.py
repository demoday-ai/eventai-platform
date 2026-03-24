"""Pydantic schemas for support chat API."""

from pydantic import BaseModel, Field


class ThreadResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_username: str | None = None
    user_role: str | None = None
    status: str
    last_message: str | None = None
    last_message_at: str | None = None
    unread: bool = False
    message_count: int = 0


class MessageResponse(BaseModel):
    id: str
    sender_type: str  # "user" | "organizer"
    sender_name: str
    text: str
    created_at: str


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class CreateThreadRequest(BaseModel):
    user_id: str
    message: str = Field(min_length=1, max_length=4000)


class ThreadListResponse(BaseModel):
    threads: list[ThreadResponse]
    total: int


class UnreadCountResponse(BaseModel):
    count: int
