"""Separate harvest season evidence from consumer-market availability.

Revision ID: 0015
Revises: 0014
"""

from alembic import context, op
import sqlalchemy as sa


revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | None = None
depends_on: str | None = None


def _count_rows(query: str) -> int:
    if context.is_offline_mode():
        return 0
    return int(op.get_bind().execute(sa.text(query)).scalar_one())


def upgrade() -> None:
    invalid_region_rows = _count_rows(
        "SELECT count(*) FROM public.fruit_seasons "
        "WHERE (region = '全国') IS DISTINCT FROM (region_level = 'national')"
    )
    if invalid_region_rows:
        raise RuntimeError(
            "Cannot enforce fruit season region semantics: "
            f"{invalid_region_rows} rows require an explicit region-level decision"
        )

    op.add_column(
        "fruit_seasons",
        sa.Column(
            "data_scope",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'legacy'"),
        ),
        schema="public",
    )
    op.add_column(
        "fruit_seasons",
        sa.Column(
            "data_quality",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'unverified'"),
        ),
        schema="public",
    )
    op.add_column(
        "fruit_seasons",
        sa.Column(
            "cultivation_type",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
        schema="public",
    )
    op.add_column(
        "fruit_seasons",
        sa.Column("source_note", sa.Text(), nullable=True),
        schema="public",
    )
    op.add_column(
        "fruit_seasons",
        sa.Column("source_year", sa.SmallInteger(), nullable=True),
        schema="public",
    )
    op.add_column(
        "fruit_seasons",
        sa.Column(
            "is_scoring_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema="public",
    )

    op.drop_constraint(
        "uq_fruit_seasons_fruit_region_months",
        "fruit_seasons",
        schema="public",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_fruit_seasons_fruit_scope_region_months",
        "fruit_seasons",
        ["fruit_id", "data_scope", "region", "start_month", "end_month"],
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_data_scope_values",
        "fruit_seasons",
        "data_scope IN ('harvest', 'market', 'legacy')",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_data_quality_values",
        "fruit_seasons",
        "data_quality IN ('high', 'medium', 'low', 'unverified')",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_cultivation_type_values",
        "fruit_seasons",
        "cultivation_type IN ('open_field', 'protected', 'mixed', 'unknown')",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_source_year_range",
        "fruit_seasons",
        "source_year IS NULL OR source_year BETWEEN 2000 AND 2100",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_source_note_length",
        "fruit_seasons",
        "source_note IS NULL OR length(source_note) <= 2000",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_region_level_contract",
        "fruit_seasons",
        "(region = '全国') = (region_level = 'national')",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_scoring_evidence",
        "fruit_seasons",
        "NOT is_scoring_enabled OR ("
        "data_scope <> 'legacy' AND data_quality IN ('high', 'medium') "
        "AND source_note IS NOT NULL AND length(btrim(source_note)) > 0 "
        "AND source_year IS NOT NULL)",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_legacy_disabled",
        "fruit_seasons",
        "data_scope <> 'legacy' OR NOT is_scoring_enabled",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_unverified_supply",
        "fruit_seasons",
        "data_scope = 'legacy' OR data_quality <> 'unverified' "
        "OR supply_status <> 'available'",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_seasons_scope_semantics",
        "fruit_seasons",
        "data_scope = 'legacy' OR "
        "(data_scope = 'harvest' AND availability_score = 0.45 "
        "AND supply_status = 'unknown') OR "
        "(data_scope = 'market' AND season_score = 0.35 "
        "AND cultivation_type = 'unknown')",
        schema="public",
    )


def downgrade() -> None:
    evidenced_rows = _count_rows(
        "SELECT count(*) FROM public.fruit_seasons "
        "WHERE data_scope <> 'legacy'"
    )
    if evidenced_rows:
        raise RuntimeError(
            "Cannot downgrade season evidence without discarding evidence: "
            f"{evidenced_rows} non-legacy rows exist"
        )

    duplicate_keys = _count_rows(
        "SELECT count(*) FROM ("
        "SELECT 1 FROM public.fruit_seasons "
        "GROUP BY fruit_id, region, start_month, end_month "
        "HAVING count(*) > 1) AS duplicate_natural_keys"
    )
    if duplicate_keys:
        raise RuntimeError(
            "Cannot downgrade season evidence without losing scope distinctions: "
            f"{duplicate_keys} duplicate legacy natural keys exist"
        )

    for name in (
        "ck_fruit_seasons_scope_semantics",
        "ck_fruit_seasons_unverified_supply",
        "ck_fruit_seasons_legacy_disabled",
        "ck_fruit_seasons_scoring_evidence",
        "ck_fruit_seasons_region_level_contract",
        "ck_fruit_seasons_source_note_length",
        "ck_fruit_seasons_source_year_range",
        "ck_fruit_seasons_cultivation_type_values",
        "ck_fruit_seasons_data_quality_values",
        "ck_fruit_seasons_data_scope_values",
    ):
        op.drop_constraint(
            name,
            "fruit_seasons",
            schema="public",
            type_="check",
        )
    op.drop_constraint(
        "uq_fruit_seasons_fruit_scope_region_months",
        "fruit_seasons",
        schema="public",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_fruit_seasons_fruit_region_months",
        "fruit_seasons",
        ["fruit_id", "region", "start_month", "end_month"],
        schema="public",
    )
    for name in (
        "is_scoring_enabled",
        "source_year",
        "source_note",
        "cultivation_type",
        "data_quality",
        "data_scope",
    ):
        op.drop_column("fruit_seasons", name, schema="public")
