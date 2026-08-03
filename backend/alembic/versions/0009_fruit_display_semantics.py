"""Add consumer-facing fruit display semantics and normalize legacy roles.

This migration deliberately keeps ``category`` for compatibility.  The new
``display_group`` column is a presentation grouping and is not read by the
recommendation core.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add and backfill display semantics without changing stable fruit IDs."""

    op.add_column(
        "fruits",
        sa.Column(
            "display_group",
            sa.String(length=80),
            nullable=True,
            server_default=sa.text("''"),
        ),
        schema="public",
    )
    op.execute(
        sa.text(
            """
            UPDATE public.fruits
            SET display_group = CASE category
                WHEN '仁果' THEN '苹果梨类'
                WHEN '核果类' THEN '桃樱类'
                WHEN '浆果类' THEN '葡萄与浆果类'
                WHEN '柑橘类' THEN '柑橘类'
                WHEN '瓜果类' THEN '瓜类'
                WHEN '热带水果' THEN '热带与特色水果'
                ELSE category
            END
            WHERE display_group IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE public.fruits
            ALTER COLUMN display_group SET NOT NULL
            """
        )
    )

    op.drop_constraint(
        "ck_fruits_daily_role_values",
        "fruits",
        schema="public",
        type_="check",
    )
    op.create_check_constraint(
        "ck_fruits_daily_role_values",
        "fruits",
        "daily_recommendation_role IN ('main', 'supporting')",
        schema="public",
    )

    op.execute(
        sa.text(
            """
            UPDATE public.fruits
            SET daily_recommendation_role = CASE
                WHEN code = 'lemon' THEN 'supporting'
                ELSE 'main'
            END,
            novelty_level = CASE
                WHEN code = 'durian' THEN 2
                WHEN code IN ('papaya', 'avocado') THEN 1
                ELSE 0
            END,
            name = CASE WHEN code = 'mandarin' THEN '橘子' ELSE name END,
            aliases = CASE
                WHEN code = 'mandarin' THEN ARRAY['柑橘']::varchar[]
                WHEN code = 'pineapple' THEN ARRAY['凤梨']::varchar[]
                WHEN code = 'cherry' THEN ARRAY['车厘子']::varchar[]
                WHEN code = 'longan' THEN ARRAY['鲜桂圆']::varchar[]
                WHEN code = 'grape' THEN ARRAY['提子']::varchar[]
                WHEN code = 'apple' THEN ARRAY[]::varchar[]
                WHEN code = 'hami_melon' THEN ARRAY[]::varchar[]
                ELSE aliases
            END,
            convenience_score = ROUND((
                0.30 * portability_score
                + 0.25 * (1 - preparation_difficulty)
                + 0.25 * (1 - messiness_score)
                + 0.20 * (1 - storage_difficulty)
            )::numeric, 3)
            """
        )
    )


def downgrade() -> None:
    """Remove only the display column and restore the legacy role constraint.

    Data values normalized by this migration are intentionally not reverted;
    restoring old role values would reintroduce the deprecated semantics.
    """

    op.drop_constraint(
        "ck_fruits_daily_role_values",
        "fruits",
        schema="public",
        type_="check",
    )
    op.create_check_constraint(
        "ck_fruits_daily_role_values",
        "fruits",
        "daily_recommendation_role IN ('main', 'exploration', 'supporting')",
        schema="public",
    )
    op.drop_column("fruits", "display_group", schema="public")
