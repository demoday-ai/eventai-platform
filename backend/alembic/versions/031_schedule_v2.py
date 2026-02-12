"""schedule v2 - slot types, room config

Revision ID: 031
Revises: 030
Create Date: 2026-02-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- schedule_slots ---
    op.add_column(
        "schedule_slots",
        sa.Column("slot_type", sa.String(20), nullable=False, server_default="project"),
    )
    op.add_column(
        "schedule_slots",
        sa.Column("title", sa.String(300), nullable=True),
    )
    op.add_column(
        "schedule_slots",
        sa.Column("description", sa.Text(), nullable=True),
    )
    # Make project_id nullable
    op.alter_column("schedule_slots", "project_id", existing_type=sa.UUID(), nullable=True)

    # Replace UniqueConstraint with partial unique index
    op.drop_constraint("uq_slot_project_run", "schedule_slots", type_="unique")
    op.create_index(
        "uq_slot_project_run_v2",
        "schedule_slots",
        ["project_id", "clustering_run_id"],
        unique=True,
        postgresql_where=text("project_id IS NOT NULL"),
    )

    # --- rooms ---
    op.add_column("rooms", sa.Column("moderator", sa.String(200), nullable=True))
    op.add_column("rooms", sa.Column("platform", sa.String(50), nullable=True))
    op.add_column(
        "rooms",
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default="15"),
    )
    op.add_column("rooms", sa.Column("day_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    # --- rooms ---
    op.drop_column("rooms", "day_number")
    op.drop_column("rooms", "slot_duration_minutes")
    op.drop_column("rooms", "platform")
    op.drop_column("rooms", "moderator")

    # --- schedule_slots ---
    op.drop_index("uq_slot_project_run_v2", table_name="schedule_slots")
    op.create_unique_constraint(
        "uq_slot_project_run", "schedule_slots", ["project_id", "clustering_run_id"]
    )
    op.alter_column("schedule_slots", "project_id", existing_type=sa.UUID(), nullable=False)
    op.drop_column("schedule_slots", "description")
    op.drop_column("schedule_slots", "title")
    op.drop_column("schedule_slots", "slot_type")
