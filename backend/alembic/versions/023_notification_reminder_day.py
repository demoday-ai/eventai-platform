"""Add reminder_day to notifications.

Revision ID: 023
Revises: 022
Create Date: 2026-02-04
"""

from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("reminder_day", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("notifications", "reminder_day")
