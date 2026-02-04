"""Add organizers table.

Revision ID: 022
Revises: 021
Create Date: 2026-02-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("telegram_id", sa.String(50), unique=True, nullable=False),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("added_by", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("organizers")
