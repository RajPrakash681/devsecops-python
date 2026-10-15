"""create appointment_events (audit trail)

Revision ID: 0003_create_appointment_events
Revises: 0002_create_appointments
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_create_appointment_events"
down_revision = "0002_create_appointments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "appointment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=True),
        sa.Column("note", sa.String(200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_appointment_events_appointment_id", "appointment_events", ["appointment_id"])
    op.create_index("ix_appointment_events_created_at", "appointment_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_appointment_events_created_at", table_name="appointment_events")
    op.drop_index("ix_appointment_events_appointment_id", table_name="appointment_events")
    op.drop_table("appointment_events")
