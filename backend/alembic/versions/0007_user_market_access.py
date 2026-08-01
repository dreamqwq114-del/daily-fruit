"""Add user purchase-condition fields.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加购买条件和网购意愿字段，当前只进入资料保存链路。"""
    op.add_column(
        "users",
        sa.Column(
            "market_access_level",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("2"),
        ),
        schema="public",
    )
    op.create_check_constraint(
        "ck_users_market_access_level_range",
        "users",
        "market_access_level BETWEEN 1 AND 3",
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column(
            "accepts_online_purchase",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema="public",
    )


def downgrade() -> None:
    """只删除本 migration 新增的购买条件字段和约束。"""
    op.drop_column("users", "accepts_online_purchase", schema="public")
    op.drop_constraint(
        "ck_users_market_access_level_range",
        "users",
        schema="public",
        type_="check",
    )
    op.drop_column("users", "market_access_level", schema="public")
