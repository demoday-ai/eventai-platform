"""Fix source for imported users.

Users created via guest import have synthetic telegram_user_id starting with
'guest-', but their source was never set to 'import'.  This migration fixes
existing records so the admin panel can filter by source.

Revision ID: 029
Revises: 028
Create Date: 2026-02-11
"""

from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE users SET source = 'import' "
        "WHERE telegram_user_id LIKE 'guest-%' AND (source IS NULL OR source = 'bot')"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users SET source = 'bot' "
        "WHERE telegram_user_id LIKE 'guest-%' AND source = 'import'"
    )
