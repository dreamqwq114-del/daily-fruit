"""Restrict browser roles from the Alembic version table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """撤销浏览器角色读取 public.alembic_version 的权限。"""
    op.execute(
        sa.text(
            """
            REVOKE ALL PRIVILEGES ON TABLE public.alembic_version FROM PUBLIC;
            DO $daily_fruit_security$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.alembic_version
                        FROM anon;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_roles WHERE rolname = 'authenticated'
                ) THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.alembic_version
                        FROM authenticated;
                END IF;
            END
            $daily_fruit_security$;
            """
        )
    )


def downgrade() -> None:
    # 回滚不能恢复浏览器访问迁移元数据，这是安全边界而不是可逆业务数据。
    pass
