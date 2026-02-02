"""Initial schema with seed data.

Revision ID: 001
Revises:
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

ROLES = [
    ("10000000-0000-0000-0000-000000000001", "organizer", "Организатор"),
    ("10000000-0000-0000-0000-000000000002", "student", "Студент"),
    ("10000000-0000-0000-0000-000000000003", "expert", "Эксперт"),
    ("10000000-0000-0000-0000-000000000004", "guest", "Гость"),
    ("10000000-0000-0000-0000-000000000005", "business", "Бизнес-партнёр"),
]

EVENT = (
    "20000000-0000-0000-0000-000000000001",
    "Demo Day 2026",
    "2026-02-06",
    "2026-02-07",
)


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    guest_subtype_enum = sa.Enum(
        "applicant", "ai_practitioner", "other", name="guest_subtype_enum"
    )
    guest_subtype_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_user_id", sa.String(20), unique=True, nullable=False, index=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("guest_subtype", guest_subtype_enum, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "event_id", name="uq_user_event_role"),
    )

    # Seed roles
    roles_table = sa.table(
        "roles",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
    )
    op.bulk_insert(
        roles_table,
        [{"id": rid, "code": code, "name": name} for rid, code, name in ROLES],
    )

    # Seed event
    events_table = sa.table(
        "events",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("start_date", sa.Date),
        sa.column("end_date", sa.Date),
    )
    op.bulk_insert(
        events_table,
        [{"id": EVENT[0], "name": EVENT[1], "start_date": EVENT[2], "end_date": EVENT[3]}],
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS guest_subtype_enum")
    op.drop_table("events")
    op.drop_table("roles")
