"""Add bot-required columns to events.

Revision ID: 039_event_bot_cols
Revises: 038_bonus_tables
Create Date: 2026-05-05

Aligns events table with bot ORM projection (bot/src/models/event.py):
- evaluation_criteria JSONB  — used by expert flow (bot/src/bot/routers/expert.py)
- timezone VARCHAR(64)       — informational, defaults Europe/Moscow
- is_active BOOLEAN          — used by /start to find current event (bot/src/bot/routers/start.py)

All columns nullable / defaulted, so existing rows remain valid.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "039_event_bot_cols"
down_revision = "038_bonus_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("evaluation_criteria", JSONB(), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Europe/Moscow",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "is_active")
    op.drop_column("events", "timezone")
    op.drop_column("events", "evaluation_criteria")
