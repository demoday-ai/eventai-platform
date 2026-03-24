"""Add needs_attention to support_threads.

Revision ID: 035_needs_attention
Revises: 034_support_chat
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa

revision = "035_needs_attention"
down_revision = "034_support_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("support_threads", sa.Column("needs_attention", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("support_threads", "needs_attention")
