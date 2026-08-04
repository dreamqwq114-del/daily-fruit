"""Add texture scoring, purchase-stage metadata, and versioned snapshots."""

from collections.abc import Sequence

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FRUIT_PROFILE_VERSION = "2026-08-texture-v1"
SCORING_MODEL_VERSION = "taste-v1"


_FRUIT_VALUES = {
    "apple": ("0.85", "0.50", "ready_to_eat", None),
    "pear": ("0.75", "0.50", "ready_to_eat", None),
    "peach": ("0.80", "0.30", "variable", "软桃通常需要更短时间内食用。"),
    "cherry": ("0.55", "0.10", "ready_to_eat", None),
    "grape": ("0.75", "0.30", "ready_to_eat", None),
    "kiwifruit": ("0.25", "0.30", "needs_ripening", "未熟时常温放置至变软，再冷藏延缓继续变软。"),
    "strawberry": ("0.30", "0.10", "ready_to_eat", None),
    "blueberry": ("0.45", "0.10", "ready_to_eat", None),
    "pomegranate": ("0.35", "0.70", "ready_to_eat", None),
    "orange": ("0.40", "0.50", "ready_to_eat", None),
    "mandarin": ("0.45", "0.30", "ready_to_eat", None),
    "pomelo": ("0.40", "0.70", "ready_to_eat", None),
    "lemon": ("0.35", "0.50", "ready_to_eat", None),
    "watermelon": ("0.70", "0.50", "ready_to_eat", None),
    "hami_melon": ("0.50", "0.30", "ready_to_eat", None),
    "banana": ("0.15", "0.30", "variable", "按表皮颜色和软硬度判断适食期。"),
    "mango": ("0.20", "0.30", "variable", "常温放置至有香气并略微软化后食用。"),
    "pineapple": ("0.45", "0.30", "ready_to_eat", None),
    "dragon_fruit": ("0.35", "0.30", "ready_to_eat", None),
    "lychee": ("0.35", "0.10", "ready_to_eat", None),
    "longan": ("0.40", "0.10", "ready_to_eat", None),
    "papaya": ("0.20", "0.30", "variable", "常温放置至果肉变软、香气明显后食用。"),
    "durian": ("0.10", "0.10", "variable", "开裂或香气明显时通常已接近适食期。"),
    "avocado": ("0.20", "0.10", "needs_ripening", "常温放置至轻按略有弹性后食用。"),
}


def _case(column: str, values: dict[str, str | None]) -> str:
    parts = [
        f"WHEN code = '{code}' THEN "
        + ("NULL" if value is None else f"'{value}'")
        for code, value in values.items()
    ]
    return f"CASE {' '.join(parts)} ELSE {column} END"


def upgrade() -> None:
    # 0011 made the score nullable but intentionally left the legacy database
    # default behind. New rows must express unknown with NULL, matching ORM.
    op.alter_column(
        "user_fruit_preferences",
        "preference_score",
        existing_type=sa.Numeric(precision=4, scale=2),
        server_default=None,
        schema="public",
    )

    for column, type_ in (
        ("texture_score", sa.Numeric(4, 3)),
        ("ripe_storage_score", sa.Numeric(4, 3)),
        ("typical_purchase_stage", sa.String(20)),
        ("ripening_note", sa.Text()),
    ):
        op.add_column("fruits", sa.Column(column, type_, nullable=True), schema="public")

    texture_values = {
        "apple": "0.85", "pear": "0.75", "peach": "0.80", "cherry": "0.55",
        "grape": "0.75", "kiwifruit": "0.25", "strawberry": "0.30", "blueberry": "0.45",
        "pomegranate": "0.35", "orange": "0.40", "mandarin": "0.45", "pomelo": "0.40",
        "lemon": "0.35", "watermelon": "0.70", "hami_melon": "0.50", "banana": "0.15",
        "mango": "0.20", "pineapple": "0.45", "dragon_fruit": "0.35", "lychee": "0.35",
        "longan": "0.40", "papaya": "0.20", "durian": "0.10", "avocado": "0.20",
    }
    ripe_values = {code: values[1] for code, values in _FRUIT_VALUES.items()}
    stage_values = {code: values[2] for code, values in _FRUIT_VALUES.items()}
    note_values = {code: values[3] for code, values in _FRUIT_VALUES.items()}
    op.execute(
        sa.text(
            "UPDATE public.fruits SET "
            f"texture_score = {_case('texture_score', texture_values)}, "
            f"ripe_storage_score = {_case('ripe_storage_score', ripe_values)}, "
            f"typical_purchase_stage = {_case('typical_purchase_stage', stage_values)}, "
            f"ripening_note = {_case('ripening_note', note_values)}"
        )
    )
    if not context.is_offline_mode():
        bind = op.get_bind()
        missing = bind.execute(
            sa.text(
                "SELECT count(*) FROM public.fruits "
                "WHERE texture_score IS NULL OR ripe_storage_score IS NULL "
                "OR typical_purchase_stage IS NULL"
            )
        ).scalar_one()
        if missing:
            raise RuntimeError(f"fruit profile backfill incomplete: {missing} rows")
    for column in ("texture_score", "ripe_storage_score", "typical_purchase_stage"):
        op.alter_column("fruits", column, schema="public", nullable=False)
    op.create_check_constraint(
        "ck_fruits_texture_score_range", "fruits",
        "texture_score BETWEEN 0 AND 1", schema="public",
    )
    op.create_check_constraint(
        "ck_fruits_ripe_storage_score_values", "fruits",
        "ripe_storage_score IN (0.10, 0.30, 0.50, 0.70, 0.90)", schema="public",
    )
    op.create_check_constraint(
        "ck_fruits_typical_purchase_stage_values", "fruits",
        "typical_purchase_stage IN ('ready_to_eat', 'needs_ripening', 'variable')",
        schema="public",
    )

    for column in (
        sa.Column("texture_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("ripe_storage_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("convenience_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("legacy_score_snapshot", JSONB(), nullable=True),
    ):
        op.add_column("fruit_selection_options", column, schema="public")
    for name, column in (
        ("texture", "texture_score"),
        ("ripe", "ripe_storage_score"),
        ("convenience", "convenience_score"),
    ):
        op.create_check_constraint(
            f"ck_fruit_selection_options_{name}_range", "fruit_selection_options",
            f"{column} IS NULL OR {column} BETWEEN 0 AND 1", schema="public",
        )
    op.create_check_constraint(
        "ck_fruit_selection_options_ripe_storage_values",
        "fruit_selection_options",
        "ripe_storage_score IS NULL OR ripe_storage_score IN "
        "(0.10, 0.30, 0.50, 0.70, 0.90)",
        schema="public",
    )
    op.create_check_constraint(
        "ck_fruit_selection_options_legacy_score_snapshot_object",
        "fruit_selection_options",
        "legacy_score_snapshot IS NULL OR "
        "jsonb_typeof(legacy_score_snapshot) = 'object'",
        schema="public",
    )
    # The parent fruit is the sole source of default scoring values. Clear
    # child overrides after preserving their exact pre-upgrade values so a
    # disposable-database downgrade can restore the 0012 behavior.
    op.execute(
        sa.text(
            "UPDATE public.fruit_selection_options SET legacy_score_snapshot = "
            "jsonb_build_object("
            "'sweet_score', sweet_score, 'sour_score', sour_score, "
            "'soft_score', soft_score, 'crisp_score', crisp_score) "
            "WHERE is_default IS TRUE"
        )
    )
    op.execute(
        sa.text(
            "UPDATE public.fruit_selection_options SET "
            "sweet_score = NULL, sour_score = NULL, soft_score = NULL, "
            "crisp_score = NULL, texture_score = NULL, ripe_storage_score = NULL, "
            "convenience_score = NULL WHERE is_default IS TRUE"
        )
    )
    op.create_check_constraint(
        "ck_fruit_selection_options_default_overrides_null",
        "fruit_selection_options",
        "is_default = false OR (sweet_score IS NULL AND sour_score IS NULL "
        "AND soft_score IS NULL AND crisp_score IS NULL AND texture_score IS NULL "
        "AND ripe_storage_score IS NULL AND convenience_score IS NULL)",
        schema="public",
    )

    op.add_column("users", sa.Column("texture_preference", sa.Numeric(4, 3), nullable=True), schema="public")
    op.add_column("users", sa.Column("texture_preference_source", sa.String(32), nullable=True), schema="public")
    op.add_column("users", sa.Column("legacy_texture_sync_source", sa.String(32), nullable=True), schema="public")
    op.execute(
        sa.text(
            "UPDATE public.users SET "
            "texture_preference = CASE "
            "WHEN soft_preference IS NOT NULL AND crisp_preference IS NOT NULL "
            "AND abs(crisp_preference - (1 - soft_preference)) <= 0.20 "
            "THEN (crisp_preference + (1 - soft_preference)) / 2 "
            "WHEN soft_preference IS NULL AND crisp_preference IS NOT NULL THEN crisp_preference "
            "WHEN soft_preference IS NOT NULL AND crisp_preference IS NULL THEN 1 - soft_preference "
            "ELSE NULL END, "
            "texture_preference_source = CASE "
            "WHEN soft_preference IS NOT NULL AND crisp_preference IS NOT NULL "
            "AND abs(crisp_preference - (1 - soft_preference)) <= 0.20 THEN 'migrated_consistent' "
            "WHEN soft_preference IS NOT NULL AND crisp_preference IS NOT NULL THEN 'legacy_conflict' "
            "WHEN soft_preference IS NULL AND crisp_preference IS NOT NULL THEN 'migrated_from_crisp' "
            "WHEN soft_preference IS NOT NULL AND crisp_preference IS NULL THEN 'migrated_from_soft' "
            "ELSE 'unset' END"
        )
    )
    op.create_check_constraint(
        "ck_users_texture_preference_range", "users",
        "texture_preference IS NULL OR texture_preference BETWEEN 0 AND 1", schema="public",
    )
    op.create_check_constraint(
        "ck_users_texture_preference_source_values", "users",
        "texture_preference_source IN ('explicit_new', 'migrated_consistent', "
        "'migrated_from_soft', 'migrated_from_crisp', 'legacy_fallback', "
        "'legacy_conflict', 'unset')",
        schema="public",
    )
    op.create_check_constraint(
        "ck_users_legacy_texture_sync_source_values", "users",
        "legacy_texture_sync_source IS NULL OR legacy_texture_sync_source IN ('derived_from_texture')",
        schema="public",
    )

    op.add_column("recommendations", sa.Column("scoring_model_version", sa.String(40), nullable=True), schema="public")
    op.add_column("recommendations", sa.Column("fruit_profile_version", sa.String(40), nullable=True), schema="public")
    op.execute(
        sa.text(
            "UPDATE public.recommendations SET scoring_model_version = 'taste-v1', "
            "fruit_profile_version = 'legacy-fruit-profile'"
        )
    )
    op.alter_column("recommendations", "scoring_model_version", schema="public", nullable=False)
    op.alter_column("recommendations", "fruit_profile_version", schema="public", nullable=False)

    for column in (
        sa.Column("effective_texture_score_snapshot", sa.Numeric(4, 3), nullable=True),
        sa.Column("effective_convenience_score_snapshot", sa.Numeric(4, 3), nullable=True),
        sa.Column("effective_ripe_storage_score_snapshot", sa.Numeric(4, 3), nullable=True),
    ):
        op.add_column("recommendation_items", column, schema="public")
    for name, column in (
        ("texture", "effective_texture_score_snapshot"),
        ("convenience", "effective_convenience_score_snapshot"),
        ("ripe", "effective_ripe_storage_score_snapshot"),
    ):
        op.create_check_constraint(
            f"ck_recommendation_items_selection_{name}_range", "recommendation_items",
            f"{column} IS NULL OR {column} BETWEEN 0 AND 1", schema="public",
        )

    op.execute(
        sa.text(
            "UPDATE public.recommendation_items AS ri "
            "SET selection_option_name_snapshot = COALESCE("
            "ri.selection_option_name_snapshot, o.name), "
            "selection_option_code_snapshot = COALESCE("
            "ri.selection_option_code_snapshot, o.code) "
            "FROM public.fruit_selection_options AS o "
            "WHERE o.id = ri.selection_option_id "
            "AND (ri.selection_option_name_snapshot IS NULL "
            "OR ri.selection_option_code_snapshot IS NULL)"
        )
    )
    op.create_check_constraint(
        "ck_recommendation_items_selection_option_snapshot_complete",
        "recommendation_items",
        "selection_option_id IS NULL OR "
        "(selection_option_name_snapshot IS NOT NULL AND "
        "selection_option_code_snapshot IS NOT NULL)",
        schema="public",
    )

    op.add_column(
        "recommendation_items",
        sa.Column("fruit_snapshot", JSONB(), nullable=True),
        schema="public",
    )
    op.add_column(
        "recommendation_items",
        sa.Column("daily_fact_snapshot", JSONB(), nullable=True),
        schema="public",
    )
    op.create_check_constraint(
        "ck_recommendation_items_fruit_snapshot_object",
        "recommendation_items",
        "fruit_snapshot IS NULL OR jsonb_typeof(fruit_snapshot) = 'object'",
        schema="public",
    )
    op.create_check_constraint(
        "ck_recommendation_items_daily_fact_snapshot_object",
        "recommendation_items",
        "daily_fact_snapshot IS NULL OR jsonb_typeof(daily_fact_snapshot) = 'object'",
        schema="public",
    )
    # Legacy recommendation rows do not have the original fruit catalog
    # version available. Freeze the best reconstructable current display at
    # migration time so future catalog edits cannot mutate history. New rows
    # are snapshotted by recommendation_application_service with the exact
    # loaded ORM graph and selected daily fact.
    op.execute(
        sa.text(
            """
            UPDATE public.recommendation_items AS ri
            SET fruit_snapshot = jsonb_build_object(
                'id', f.id,
                'created_at', f.created_at,
                'updated_at', f.updated_at,
                'code', f.code,
                'name', f.name,
                'aliases', f.aliases,
                'category', f.category,
                'display_group', f.display_group,
                'taste', f.taste,
                'sweet_score', f.sweet_score,
                'sour_score', f.sour_score,
                'soft_score', f.soft_score,
                'crisp_score', f.crisp_score,
                'texture_score', f.texture_score,
                'convenience_score', f.convenience_score,
                'ripe_storage_score', f.ripe_storage_score,
                'typical_purchase_stage', f.typical_purchase_stage,
                'ripening_note', f.ripening_note,
                'average_price_level', f.average_price_level,
                'default_portion', f.default_portion,
                'default_portion_grams', f.default_portion_grams,
                'direct_eating', f.direct_eating,
                'consumption_mode', f.consumption_mode,
                'daily_recommendation_role', f.daily_recommendation_role,
                'preparation_difficulty', f.preparation_difficulty,
                'portability_score', f.portability_score,
                'messiness_score', f.messiness_score,
                'storage_difficulty', f.storage_difficulty,
                'aroma_intensity', f.aroma_intensity,
                'commonness_score', f.commonness_score,
                'novelty_level', f.novelty_level,
                'data_quality', f.data_quality,
                'data_source_note', f.data_source_note,
                'image_url', f.image_url,
                'description', f.description,
                'is_active', f.is_active,
                'nutrition', (
                    SELECT CASE WHEN n.id IS NULL THEN NULL ELSE jsonb_build_object(
                        'id', n.id,
                        'fruit_id', n.fruit_id,
                        'created_at', n.created_at,
                        'updated_at', n.updated_at,
                        'energy', n.energy,
                        'vitamin_c', n.vitamin_c,
                        'fiber', n.fiber,
                        'potassium', n.potassium,
                        'folate', n.folate,
                        'carotenoids', n.carotenoids
                    ) END
                    FROM public.fruit_nutritions AS n
                    WHERE n.fruit_id = f.id
                ),
                'seasons', COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'id', s.id,
                        'fruit_id', s.fruit_id,
                        'created_at', s.created_at,
                        'region', s.region,
                        'region_level', s.region_level,
                        'start_month', s.start_month,
                        'end_month', s.end_month,
                        'season_score', s.season_score,
                        'availability_score', s.availability_score,
                        'supply_status', s.supply_status
                    ) ORDER BY s.id)
                    FROM public.fruit_seasons AS s
                    WHERE s.fruit_id = f.id
                ), '[]'::jsonb),
                'selection_options', COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'id', o.id,
                        'fruit_id', o.fruit_id,
                        'code', o.code,
                        'name', o.name,
                        'sweet_score', o.sweet_score,
                        'sour_score', o.sour_score,
                        'soft_score', o.soft_score,
                        'crisp_score', o.crisp_score,
                        'texture_score', o.texture_score,
                        'ripe_storage_score', o.ripe_storage_score,
                        'convenience_score', o.convenience_score,
                        'is_default', o.is_default,
                        'is_active', o.is_active,
                        'display_order', o.display_order,
                        'data_quality', o.data_quality,
                        'data_source_note', o.data_source_note,
                        'created_at', o.created_at,
                        'updated_at', o.updated_at
                    ) ORDER BY o.display_order, o.id)
                    FROM public.fruit_selection_options AS o
                    WHERE o.fruit_id = f.id
                ), '[]'::jsonb)
            ),
            daily_fact_snapshot = (
                SELECT jsonb_build_object(
                    'id', fact.id,
                    'fruit_id', fact.fruit_id,
                    'fact_type', fact.fact_type,
                    'fact_text', fact.fact_text,
                    'sort_order', fact.sort_order,
                    'is_active', fact.is_active,
                    'source_note', fact.source_note,
                    'created_at', fact.created_at,
                    'updated_at', fact.updated_at
                )
                FROM (
                    SELECT ff.*,
                        row_number() OVER (
                            ORDER BY ff.sort_order, ff.id
                        ) - 1 AS fact_index,
                        count(*) OVER () AS fact_count
                    FROM public.fruit_facts AS ff
                    WHERE ff.fruit_id = f.id AND ff.is_active
                ) AS fact
                WHERE fact.fact_index = MOD(
                    (r.recommendation_date - DATE '0001-01-01' + 1)
                    + COALESCE((
                        SELECT SUM(chars.position * ascii(substr(f.code, chars.position, 1)))
                        FROM generate_series(1, length(f.code)) AS chars(position)
                    ), 0),
                    fact.fact_count
                )
            )
            FROM public.recommendations AS r, public.fruits AS f
            WHERE r.id = ri.recommendation_id
              AND f.id = ri.fruit_id
              AND ri.fruit_snapshot IS NULL
            """
        )
    )
    if not context.is_offline_mode():
        bind = op.get_bind()
        missing_snapshots = bind.execute(
            sa.text(
                "SELECT count(*) FROM public.recommendation_items "
                "WHERE fruit_snapshot IS NULL"
            )
        ).scalar_one()
        if missing_snapshots:
            raise RuntimeError(
                f"recommendation fruit snapshot backfill incomplete: {missing_snapshots} rows"
            )
    op.alter_column(
        "recommendation_items",
        "fruit_snapshot",
        schema="public",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_recommendation_items_selection_option_snapshot_complete",
        "recommendation_items",
        schema="public",
        type_="check",
    )
    for name in (
        "ck_recommendation_items_daily_fact_snapshot_object",
        "ck_recommendation_items_fruit_snapshot_object",
        "ck_recommendation_items_selection_ripe_range",
        "ck_recommendation_items_selection_convenience_range",
        "ck_recommendation_items_selection_texture_range",
    ):
        op.drop_constraint(name, "recommendation_items", schema="public", type_="check")
    for column in (
        "daily_fact_snapshot",
        "fruit_snapshot",
        "effective_ripe_storage_score_snapshot",
        "effective_convenience_score_snapshot",
        "effective_texture_score_snapshot",
    ):
        op.drop_column("recommendation_items", column, schema="public")
    op.drop_column("recommendations", "fruit_profile_version", schema="public")
    op.drop_column("recommendations", "scoring_model_version", schema="public")

    for name in (
        "ck_users_legacy_texture_sync_source_values",
        "ck_users_texture_preference_source_values",
        "ck_users_texture_preference_range",
    ):
        op.drop_constraint(name, "users", schema="public", type_="check")
    for column in ("legacy_texture_sync_source", "texture_preference_source", "texture_preference"):
        op.drop_column("users", column, schema="public")

    op.drop_constraint(
        "ck_fruit_selection_options_default_overrides_null",
        "fruit_selection_options", schema="public", type_="check",
    )
    op.execute(
        sa.text(
            "UPDATE public.fruit_selection_options SET "
            "sweet_score = (legacy_score_snapshot ->> 'sweet_score')::numeric, "
            "sour_score = (legacy_score_snapshot ->> 'sour_score')::numeric, "
            "soft_score = (legacy_score_snapshot ->> 'soft_score')::numeric, "
            "crisp_score = (legacy_score_snapshot ->> 'crisp_score')::numeric "
            "WHERE legacy_score_snapshot IS NOT NULL"
        )
    )
    op.drop_constraint(
        "ck_fruit_selection_options_legacy_score_snapshot_object",
        "fruit_selection_options", schema="public", type_="check",
    )
    op.drop_constraint(
        "ck_fruit_selection_options_ripe_storage_values",
        "fruit_selection_options", schema="public", type_="check",
    )
    for name in ("convenience", "ripe", "texture"):
        op.drop_constraint(
            f"ck_fruit_selection_options_{name}_range",
            "fruit_selection_options", schema="public", type_="check",
        )
    for column in (
        "legacy_score_snapshot", "convenience_score", "ripe_storage_score", "texture_score"
    ):
        op.drop_column("fruit_selection_options", column, schema="public")

    for name in (
        "ck_fruits_typical_purchase_stage_values",
        "ck_fruits_ripe_storage_score_values",
        "ck_fruits_texture_score_range",
    ):
        op.drop_constraint(name, "fruits", schema="public", type_="check")
    for column in ("ripening_note", "typical_purchase_stage", "ripe_storage_score", "texture_score"):
        op.drop_column("fruits", column, schema="public")

    op.alter_column(
        "user_fruit_preferences",
        "preference_score",
        existing_type=sa.Numeric(precision=4, scale=2),
        server_default=sa.text("0"),
        schema="public",
    )
