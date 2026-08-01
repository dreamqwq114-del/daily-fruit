"""Add fruit identity, availability, familiarity and discovery fields.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """扩展水果身份、供应、熟悉度和详细便利性字段。"""
    op.add_column(
        "fruits",
        sa.Column("code", sa.String(length=60), nullable=True),
        schema="public",
    )
    op.add_column(
        "fruits",
        sa.Column(
            "aliases",
    sa.ARRAY(sa.String(length=100)),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
        schema="public",
    )
    op.add_column(
        "fruits",
        sa.Column(
            "default_portion_grams",
            sa.Numeric(7, 2),
            nullable=False,
            server_default=sa.text("100"),
        ),
        schema="public",
    )
    op.add_column(
        "fruits",
        sa.Column(
            "direct_eating",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        schema="public",
    )
    op.add_column(
        "fruits",
        sa.Column(
            "consumption_mode",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'direct'"),
        ),
        schema="public",
    )
    op.add_column(
        "fruits",
        sa.Column(
            "daily_recommendation_role",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'main'"),
        ),
        schema="public",
    )
    for name in (
        "preparation_difficulty",
        "portability_score",
        "messiness_score",
        "storage_difficulty",
        "aroma_intensity",
        "commonness_score",
    ):
        op.add_column(
            "fruits",
            sa.Column(
                name,
                sa.Numeric(4, 3),
                nullable=False,
                server_default=sa.text("0.5"),
            ),
            schema="public",
        )
    op.add_column(
        "fruits",
        sa.Column(
            "novelty_level",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        schema="public",
    )
    op.add_column(
        "fruits",
        sa.Column(
            "data_quality",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'low'"),
        ),
        schema="public",
    )
    op.add_column(
        "fruits",
        sa.Column("data_source_note", sa.Text(), nullable=True),
        schema="public",
    )
    op.execute(
        sa.text(
            "UPDATE public.fruits SET code = 'legacy-' || id::text "
            "WHERE code IS NULL"
        )
    )
    op.alter_column(
        "fruits",
        "code",
        nullable=False,
        schema="public",
    )
    op.create_unique_constraint(
        "uq_fruits_code",
        "fruits",
        ["code"],
        schema="public",
    )
    for name, expression in {
        "ck_fruits_default_portion_grams_positive":
        "default_portion_grams > 0",
        "ck_fruits_preparation_difficulty_range":
        "preparation_difficulty BETWEEN 0 AND 1",
        "ck_fruits_portability_score_range":
        "portability_score BETWEEN 0 AND 1",
        "ck_fruits_messiness_score_range":
        "messiness_score BETWEEN 0 AND 1",
        "ck_fruits_storage_difficulty_range":
        "storage_difficulty BETWEEN 0 AND 1",
        "ck_fruits_aroma_intensity_range":
        "aroma_intensity BETWEEN 0 AND 1",
        "ck_fruits_commonness_score_range":
        "commonness_score BETWEEN 0 AND 1",
        "ck_fruits_novelty_level_range":
        "novelty_level BETWEEN 0 AND 2",
        "ck_fruits_consumption_mode_values":
        "consumption_mode IN ('direct', 'peel', 'cut', 'ingredient')",
        "ck_fruits_daily_role_values":
        "daily_recommendation_role IN ('main', 'exploration', 'supporting')",
        "ck_fruits_data_quality_values":
        "data_quality IN ('high', 'medium', 'low')",
    }.items():
        op.create_check_constraint(name, "fruits", expression, schema="public")

    op.add_column(
        "fruit_seasons",
        sa.Column(
            "region_level",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'national'"),
        ),
        schema="public",
    )
    op.add_column(
        "fruit_seasons",
        sa.Column(
            "availability_score",
            sa.Numeric(4, 3),
            nullable=False,
            server_default=sa.text("0.45"),
        ),
        schema="public",
    )
    op.add_column(
        "fruit_seasons",
        sa.Column(
            "supply_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_region_level_values",
        "fruit_seasons",
        "region_level IN ('city', 'province', 'area', 'national')",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_availability_score_range",
        "fruit_seasons",
        "availability_score BETWEEN 0 AND 1",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_supply_status_values",
        "fruit_seasons",
        "supply_status IN ('available', 'unknown', 'unavailable')",
        schema="public",
    )

    op.add_column(
        "users",
        sa.Column(
            "discovery_level",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        schema="public",
    )
    for name in (
        "sweet_preference",
        "sour_preference",
        "soft_preference",
        "crisp_preference",
    ):
        op.alter_column(
            "users",
            name,
            nullable=True,
            schema="public",
        )
    op.create_check_constraint(
        "ck_users_discovery_level_range",
        "users",
        "discovery_level BETWEEN 0 AND 2",
        schema="public",
    )

    op.add_column(
        "user_fruit_preferences",
        sa.Column("has_tried", sa.Boolean(), nullable=True),
        schema="public",
    )
    op.add_column(
        "user_fruit_preferences",
        sa.Column("willing_to_try", sa.Boolean(), nullable=True),
        schema="public",
    )
    op.drop_constraint(
        "ck_user_fruit_preferences_score_range",
        "user_fruit_preferences",
        schema="public",
        type_="check",
    )
    op.create_check_constraint(
        "ck_user_fruit_preferences_score_range",
        "user_fruit_preferences",
        "preference_score IS NULL OR preference_score BETWEEN -1 AND 2",
        schema="public",
    )

    for name in ("individual_score", "pair_score", "nutrition_pair_score"):
        op.add_column(
            "recommendation_items",
            sa.Column(
                name,
                sa.Numeric(8, 6),
                nullable=True,
            ),
            schema="public",
        )
    op.execute(
        sa.text(
            "UPDATE public.recommendation_items "
            "SET individual_score = score, pair_score = score, "
            "nutrition_pair_score = 0 "
            "WHERE individual_score IS NULL"
        )
    )
    for name in ("individual_score", "pair_score", "nutrition_pair_score"):
        op.alter_column(
            "recommendation_items",
            name,
            nullable=False,
            schema="public",
        )
    op.create_check_constraint(
        "ck_recommendation_items_individual_score_range",
        "recommendation_items",
        "individual_score BETWEEN 0 AND 1",
        schema="public",
    )
    op.create_check_constraint(
        "ck_recommendation_items_pair_score_range",
        "recommendation_items",
        "pair_score BETWEEN 0 AND 1",
        schema="public",
    )
    op.create_check_constraint(
        "ck_recommendation_items_nutrition_pair_score_range",
        "recommendation_items",
        "nutrition_pair_score BETWEEN 0 AND 1",
        schema="public",
    )


def downgrade() -> None:
    """按依赖相反顺序删除 V2 新增的水果/偏好对象。"""
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM public.user_fruit_preferences "
            "WHERE preference_score IS NULL OR has_tried IS NOT NULL "
            "OR willing_to_try IS NOT NULL) OR EXISTS ("
            "SELECT 1 FROM public.users WHERE sweet_preference IS NULL "
            "OR sour_preference IS NULL OR soft_preference IS NULL "
            "OR crisp_preference IS NULL) OR EXISTS ("
            "SELECT 1 FROM public.recommendation_items "
            "WHERE individual_score <> score OR pair_score <> score "
            "OR nutrition_pair_score <> 0) THEN "
            "RAISE EXCEPTION '0005 downgrade would discard V2 data'; "
            "END IF; END $$;"
        )
    )
    for name in (
        "ck_recommendation_items_nutrition_pair_score_range",
        "ck_recommendation_items_pair_score_range",
        "ck_recommendation_items_individual_score_range",
    ):
        op.drop_constraint(
            name,
            "recommendation_items",
            schema="public",
            type_="check",
        )
    for name in ("nutrition_pair_score", "pair_score", "individual_score"):
        op.drop_column("recommendation_items", name, schema="public")

    op.drop_constraint(
        "ck_user_fruit_preferences_score_range",
        "user_fruit_preferences",
        schema="public",
        type_="check",
    )
    op.create_check_constraint(
        "ck_user_fruit_preferences_score_range",
        "user_fruit_preferences",
        "preference_score BETWEEN -1 AND 2",
        schema="public",
    )
    op.drop_column("user_fruit_preferences", "willing_to_try", schema="public")
    op.drop_column("user_fruit_preferences", "has_tried", schema="public")

    op.drop_constraint(
        "ck_users_discovery_level_range",
        "users",
        schema="public",
        type_="check",
    )
    op.drop_column("users", "discovery_level", schema="public")
    for name in (
        "sweet_preference",
        "sour_preference",
        "soft_preference",
        "crisp_preference",
    ):
        op.alter_column(
            "users",
            name,
            nullable=False,
            schema="public",
        )

    for name in (
        "ck_fruit_seasons_supply_status_values",
        "ck_fruit_seasons_availability_score_range",
        "ck_fruit_seasons_region_level_values",
    ):
        op.drop_constraint(name, "fruit_seasons", schema="public", type_="check")
    for name in ("supply_status", "availability_score", "region_level"):
        op.drop_column("fruit_seasons", name, schema="public")

    for name in (
        "ck_fruits_data_quality_values",
        "ck_fruits_daily_role_values",
        "ck_fruits_consumption_mode_values",
        "ck_fruits_novelty_level_range",
        "ck_fruits_commonness_score_range",
        "ck_fruits_aroma_intensity_range",
        "ck_fruits_storage_difficulty_range",
        "ck_fruits_messiness_score_range",
        "ck_fruits_portability_score_range",
        "ck_fruits_preparation_difficulty_range",
        "ck_fruits_default_portion_grams_positive",
    ):
        op.drop_constraint(name, "fruits", schema="public", type_="check")
    op.drop_constraint("uq_fruits_code", "fruits", schema="public", type_="unique")
    for name in (
        "data_source_note",
        "data_quality",
        "novelty_level",
        "commonness_score",
        "aroma_intensity",
        "storage_difficulty",
        "messiness_score",
        "portability_score",
        "preparation_difficulty",
        "daily_recommendation_role",
        "consumption_mode",
        "direct_eating",
        "default_portion_grams",
        "aliases",
        "code",
    ):
        op.drop_column("fruits", name, schema="public")
