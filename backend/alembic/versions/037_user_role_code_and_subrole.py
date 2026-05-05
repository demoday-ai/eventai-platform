"""Add users.role_code and users.subrole for bonus-track-llm bot.

Revision ID: 037_user_role_code
Revises: 036_pgvector_projects
Create Date: 2026-05-03

Adds coarse role classification (guest|business|expert) used by the new bot agent
alongside the legacy 8-value guest_subtype enum used by admin UI.

Backfills role_code from guest_subtype:
  student | applicant | other         -> guest
  investor | business_partner | hr     -> business
  mentor | jury                        -> expert
"""

from alembic import op
import sqlalchemy as sa


revision = "037_user_role_code"
down_revision = "036_pgvector_projects"
branch_labels = None
depends_on = None


USER_ROLE_CODE_VALUES = ("guest", "business", "expert")


def upgrade() -> None:
    # 1. Create enum type
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE user_role_code AS ENUM ('guest', 'business', 'expert'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    # 2. Add columns (nullable, no defaults)
    op.add_column(
        "users",
        sa.Column(
            "role_code",
            sa.Enum(*USER_ROLE_CODE_VALUES, name="user_role_code", create_type=False),
            nullable=True,
        ),
    )
    op.add_column("users", sa.Column("subrole", sa.String(128), nullable=True))

    # 3. Backfill role_code from guest_subtype.
    # Notes:
    # - guest_subtype_enum stores values as uppercase (STUDENT, APPLICANT, ...)
    #   because SQLAlchemy serializes Python Enum.name, not Enum.value.
    # - We compare via ::text cast so PostgreSQL doesn't refuse fresh enum
    #   labels added in earlier migrations within the same alembic transaction
    #   (UnsafeNewEnumValueUsageError).
    op.execute(
        """
        UPDATE users SET role_code = CASE
            WHEN guest_subtype::text IN ('STUDENT', 'APPLICANT', 'OTHER') THEN 'guest'::user_role_code
            WHEN guest_subtype::text IN ('INVESTOR', 'BUSINESS_PARTNER', 'HR') THEN 'business'::user_role_code
            WHEN guest_subtype::text IN ('MENTOR', 'JURY') THEN 'expert'::user_role_code
            ELSE NULL
        END
        WHERE guest_subtype IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("users", "subrole")
    op.drop_column("users", "role_code")
    # Drop enum type only if no other tables reference it
    op.execute("DROP TYPE IF EXISTS user_role_code")
