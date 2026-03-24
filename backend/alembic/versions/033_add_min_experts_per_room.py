"""Add min_experts_per_room to events.

Revision ID: 033_min_experts
Revises: 032_add_id_to_tour_status
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa

revision = "033_min_experts"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("min_experts_per_room", sa.Integer(), nullable=False, server_default="2"))


def downgrade() -> None:
    op.drop_column("events", "min_experts_per_room")
