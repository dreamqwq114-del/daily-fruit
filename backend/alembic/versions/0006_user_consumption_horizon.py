"""Add the user preference consumption horizon.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "consumption_horizon_days",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("4"),
        ),
        schema="public",
    )
    op.create_check_constraint(
        "ck_users_consumption_horizon_days_values",
        "users",
        "consumption_horizon_days IN (2, 4, 7)",
        schema="public",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_users_consumption_horizon_days_values",
        "users",
        schema="public",
        type_="check",
    )
    op.drop_column("users", "consumption_horizon_days", schema="public")
