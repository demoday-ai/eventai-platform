"""Add skipped status to notification_status_enum for EPIC-007b.

Revision ID: 007
Revises: 006
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'skipped' value to notification_status_enum
    op.execute(sa.text(
        "ALTER TYPE notification_status_enum ADD VALUE IF NOT EXISTS 'skipped'"
    ))


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values easily
    # Would need to recreate the enum type, which is complex
    # For now, leave the enum value in place (it's harmless)
    pass
