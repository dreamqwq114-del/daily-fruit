"""Link business users to external authentication identities.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_user_id", sa.Uuid(), nullable=True),
        schema="public",
    )
    op.create_unique_constraint(
        "uq_users_auth_user_id",
        "users",
        ["auth_user_id"],
        schema="public",
    )
    op.create_foreign_key(
        "fk_users_auth_user_id_users",
        "users",
        "users",
        ["auth_user_id"],
        ["id"],
        source_schema="public",
        referent_schema="auth",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_users_auth_user_id_users",
        "users",
        schema="public",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_users_auth_user_id",
        "users",
        schema="public",
        type_="unique",
    )
    op.drop_column("users", "auth_user_id", schema="public")
