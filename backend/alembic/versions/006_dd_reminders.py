"""Add reminder tables for EPIC-007 DD Reminders.

Revision ID: 006
Revises: 005
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (safe with DO block for duplicate prevention)
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE reminder_type_enum AS ENUM ('day_before', 'hour_before'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    ))
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE reminder_batch_status_enum AS ENUM "
        "('preview', 'confirmed', 'in_progress', 'completed', 'cancelled'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    ))
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE notification_status_enum AS ENUM ('pending', 'sent', 'failed'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    ))
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE recipient_type_enum AS ENUM ('student', 'expert', 'guest', 'business'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    ))

    # Use ENUM with create_type=False to avoid duplicate creation
    reminder_type = ENUM(
        "day_before", "hour_before",
        name="reminder_type_enum",
        create_type=False,
    )
    batch_status = ENUM(
        "preview", "confirmed", "in_progress", "completed", "cancelled",
        name="reminder_batch_status_enum",
        create_type=False,
    )
    notification_status = ENUM(
        "pending", "sent", "failed",
        name="notification_status_enum",
        create_type=False,
    )
    recipient_type = ENUM(
        "student", "expert", "guest", "business",
        name="recipient_type_enum",
        create_type=False,
    )

    # Create reminder_batches table
    op.create_table(
        "reminder_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reminder_type", reminder_type, nullable=False),
        sa.Column("initiated_by", sa.String(20), nullable=False),
        sa.Column("initiated_by_name", sa.String(200), nullable=True),
        sa.Column("total_recipients", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", batch_status, nullable=False, server_default="preview"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_reminder_batches_event_id", "reminder_batches", ["event_id"])
    op.create_index("ix_reminder_batches_status", "reminder_batches", ["status"])

    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            UUID(as_uuid=True),
            sa.ForeignKey("reminder_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipient_type", recipient_type, nullable=False),
        sa.Column("telegram_user_id", sa.String(20), nullable=False),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "expert_id",
            UUID(as_uuid=True),
            sa.ForeignKey("experts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "participation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("participation_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", notification_status, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("message_text", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_notifications_batch_id", "notifications", ["batch_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_telegram_user_id", "notifications", ["telegram_user_id"])

    # Add telegram_chat_id to experts
    op.add_column("experts", sa.Column("telegram_chat_id", sa.String(20), nullable=True))
    op.create_index("ix_experts_telegram_chat_id", "experts", ["telegram_chat_id"])


def downgrade() -> None:
    # Drop expert column
    op.drop_index("ix_experts_telegram_chat_id", "experts")
    op.drop_column("experts", "telegram_chat_id")

    # Drop tables
    op.drop_table("notifications")
    op.drop_table("reminder_batches")

    # Drop enum types
    op.execute(sa.text("DROP TYPE IF EXISTS notification_status_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS recipient_type_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS reminder_batch_status_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS reminder_type_enum"))
