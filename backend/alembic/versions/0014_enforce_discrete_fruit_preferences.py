"""Enforce discrete fruit preference and willingness state contracts."""

from alembic import context, op
import sqlalchemy as sa


revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | None = None
depends_on: str | None = None


def _count_invalid_rows(query: str) -> int:
    if context.is_offline_mode():
        return 0
    return int(op.get_bind().execute(sa.text(query)).scalar_one())


def upgrade() -> None:
    fractional_count = _count_invalid_rows(
        "SELECT count(*) FROM public.user_fruit_preferences "
        "WHERE preference_score IS NOT NULL "
        "AND preference_score NOT IN (-1, 0, 1, 2)"
    )
    if fractional_count:
        raise RuntimeError(
            "Cannot enforce discrete fruit preferences: "
            f"{fractional_count} non-discrete rows require an explicit data decision"
        )

    invalid_willingness_count = _count_invalid_rows(
        "SELECT count(*) FROM public.user_fruit_preferences "
        "WHERE willing_to_try IS NOT NULL "
        "AND has_tried IS DISTINCT FROM false"
    )
    if invalid_willingness_count:
        raise RuntimeError(
            "Cannot enforce fruit willingness state: "
            f"{invalid_willingness_count} contradictory rows require an explicit data decision"
        )

    op.drop_constraint("ck_user_fruit_preferences_score_range", "user_fruit_preferences", schema="public", type_="check")
    op.create_check_constraint(
        "ck_user_fruit_preferences_score_range",
        "user_fruit_preferences",
        "preference_score IS NULL OR preference_score IN (-1, 0, 1, 2)",
        schema="public",
    )
    op.create_check_constraint(
        "ck_user_fruit_preferences_willingness_state",
        "user_fruit_preferences",
        "willing_to_try IS NULL OR has_tried IS FALSE",
        schema="public",
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_fruit_preferences_willingness_state", "user_fruit_preferences", schema="public", type_="check")
    op.drop_constraint("ck_user_fruit_preferences_score_range", "user_fruit_preferences", schema="public", type_="check")
    op.create_check_constraint(
        "ck_user_fruit_preferences_score_range",
        "user_fruit_preferences",
        "preference_score IS NULL OR preference_score BETWEEN -1 AND 2",
        schema="public",
    )
