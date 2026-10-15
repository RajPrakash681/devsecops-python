"""create doctors

Revision ID: 0001_create_doctors
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_doctors"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("specialty", sa.String(60), nullable=False),
        sa.Column("room", sa.String(20), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("doctors")
