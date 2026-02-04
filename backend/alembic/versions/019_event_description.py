"""Add description column to events table.

Revision ID: 019
Revises: 018
Create Date: 2026-02-04
"""

from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("description", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("events", "description")
