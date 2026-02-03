"""Pydantic schemas for EPIC-007: DD Reminders.

Schemas per contracts/api.yaml.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.reminder import (
    NotificationStatus,
    RecipientType,
    ReminderBatchStatus,
    ReminderType,
)


class RolePreview(BaseModel):
    """Preview counts for a single role."""

    count: int  # Recipients with Telegram
    skipped: int  # Recipients without Telegram
    declined: int | None = None  # Declined (experts only)


class ReminderPreview(BaseModel):
    """Preview of reminder recipients before sending."""

    reminder_type: ReminderType
    by_role: dict[str, RolePreview]  # students, experts, guests, business
    total_recipients: int
    total_skipped: int
    duplicate_warning: dict | None = None  # {last_batch_id, minutes_ago}


class NotificationSummary(BaseModel):
    """Summary of an individual notification."""

    id: UUID
    recipient_type: RecipientType
    recipient_name: str | None = None
    status: NotificationStatus
    error_message: str | None = None
    sent_at: datetime | None = None


class ReminderBatchSummary(BaseModel):
    """Summary of a reminder batch."""

    id: UUID
    reminder_type: ReminderType
    status: ReminderBatchStatus
    initiated_by_name: str | None = None
    total_recipients: int
    sent_count: int
    failed_count: int
    skipped_count: int
    started_at: datetime
    completed_at: datetime | None = None


class ReminderBatchDetail(ReminderBatchSummary):
    """Detailed view of a reminder batch with notifications."""

    notifications: list[NotificationSummary] = []
    by_recipient_type: dict[str, dict] | None = None  # {role: {total, sent, failed}}


class ReminderBatchListResponse(BaseModel):
    """Response for listing reminder batches."""

    batches: list[ReminderBatchSummary]
