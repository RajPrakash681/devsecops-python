"""create appointments

Revision ID: 0002_create_appointments
Revises: 0001_create_doctors
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_create_appointments"
down_revision = "0001_create_doctors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        # RESTRICT: a doctor with appointment history cannot be deleted, only deactivated.
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_name", sa.String(100), nullable=False),
        sa.Column("patient_phone", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="BOOKED"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        # The database refuses impossible rows even if a bug slips past the API.
        sa.CheckConstraint("ends_at > starts_at", name="ck_appointments_time_order"),
        sa.CheckConstraint("status IN ('BOOKED', 'CHECKED_IN', 'COMPLETED', 'CANCELLED', 'NO_SHOW')",
                           name="ck_appointments_status"),
    )
    # The overlap check and the day view both filter on (doctor, start time).
    op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"])
    op.create_index("ix_appointments_starts_at", "appointments", ["starts_at"])


def downgrade() -> None:
    op.drop_index("ix_appointments_starts_at", table_name="appointments")
    op.drop_index("ix_appointments_doctor_id", table_name="appointments")
    op.drop_table("appointments")
