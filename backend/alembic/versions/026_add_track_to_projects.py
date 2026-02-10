"""Add track field to projects table.

Track represents the project category: industrial, startup, educational, research.

Revision ID: 026
Revises: 025
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("track", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "track")
