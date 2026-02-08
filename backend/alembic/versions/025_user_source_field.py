"""Add source field to users table.

Tracks where the user record was created from: 'bot' (default) or 'import'.

Revision ID: 025
Revises: 024
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("source", sa.String(10), nullable=True, server_default="bot"),
    )


def downgrade() -> None:
    op.drop_column("users", "source")
