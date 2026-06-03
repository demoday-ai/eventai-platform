"""Add taken_over flag to support_threads (conversation takeover).

Revision ID: 041_conversation_takeover
Revises: 039_event_bot_cols
Create Date: 2026-06-03

When an organizer replies from the admin, the conversation is "taken over":
the AI agent stops auto-replying in that chat until released.
"""

from alembic import op
import sqlalchemy as sa

revision = "041_conversation_takeover"
down_revision = "039_event_bot_cols"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "support_threads",
        sa.Column("taken_over", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("support_threads", "taken_over")
