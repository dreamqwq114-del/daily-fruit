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
    # A downgrade must never restore browser access to migration metadata.
    pass
