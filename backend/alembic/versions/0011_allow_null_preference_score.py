"""Allow empty preference scores for forbidden fruits.

The API uses ``preference_score = NULL`` together with ``is_forbidden = true``
to distinguish an explicit prohibition from a neutral preference.  The
existing check constraint already permits NULL, but the original column was
still marked NOT NULL.  This migration aligns the live schema with the ORM
and request contract without changing existing rows or the default value.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow NULL scores while preserving the existing default and checks."""

    op.alter_column(
        "user_fruit_preferences",
        "preference_score",
        existing_type=sa.Numeric(precision=4, scale=2),
        nullable=True,
        schema="public",
    )


def downgrade() -> None:
    """Restore NOT NULL only when no forbidden rows use a NULL score.

    PostgreSQL will reject this operation if NULL scores exist.  That is
    intentional: silently converting them to zero would erase the distinction
    between a forbidden fruit and a neutral preference.
    """

    op.alter_column(
        "user_fruit_preferences",
        "preference_score",
        existing_type=sa.Numeric(precision=4, scale=2),
        nullable=False,
        schema="public",
    )
