"""Deterministic fixed-profile comparison for the texture-v2 rollout.

The v1 side is an immutable artifact captured from the rewritten pre-switch
commit.  The v2 side runs the current production core with the complete parent
and selection-option catalog.  This is a synthetic regression audit, not a
claim about production-user change rates.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from statistics import mean, pstdev

from app.seed.seed_fruits import load_seed_dataset
from app.services.recommendation_core.pair_selection import (
    PAIR_NEAR_TOP_THRESHOLD,
    select_recommendation_pair,
)
from app.services.recommendation_service import recommend_fruits, score_candidates
from app.services.recommendation_types import (
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    NutritionProfile,
    SeasonWindow,
    SelectionOption,
)


ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = ROOT / "data" / "recommendation_v1_audit_baseline.json"
BASELINE_SCHEMA_VERSION = 1
V1_SOURCE_REVISION = "e942a72db148b7b3e30a6d21f04d9f7f99104914"
BASELINE_GENERATION_CONTRACT = "full_seed_catalog_ordered_ranking_pair_and_reasons"
AUDIT_SINGLE_NEAR_TOP_THRESHOLD = 0.02
COMPARISON_SCOPE = "fixed_synthetic_profiles_with_selection_options"
COMPARISON_LABEL = "固定合成画像对比"
PROFILE_NAMES = (
    "biased_sweet_crisp",
    "sweet_soft",
    "sour_crisp",
    "sour_soft",
    "high_sweet_sour",
    "sweet_only",
    "texture_only",
    "sour_only",
    "no_sensory",
    "migrated_consistent",
    "migrated_conflict",
)


def _selection_options_by_fruit(
    fruit_ids: dict[str, int],
) -> dict[str, tuple[SelectionOption, ...]]:
    rows = json.loads(
        (ROOT / "data" / "fruit_selection_options_seed.json").read_text(
            encoding="utf-8"
        )
    )
    grouped: dict[str, list[SelectionOption]] = {}
    for option_id, row in enumerate(rows, start=1_001):
        fruit_code = str(row["fruit_code"])
        grouped.setdefault(fruit_code, []).append(
            SelectionOption(
                id=option_id,
                fruit_id=fruit_ids[fruit_code],
                code=str(row["code"]),
                name=str(row["name"]),
                sweet_score=row.get("sweet_score"),
                sour_score=row.get("sour_score"),
                soft_score=row.get("soft_score"),
                crisp_score=row.get("crisp_score"),
                texture_score=row.get("texture_score"),
                ripe_storage_score=row.get("ripe_storage_score"),
                convenience_score=row.get("convenience_score"),
                is_default=bool(row["is_default"]),
                is_active=bool(row["is_active"]),
                display_order=int(row["display_order"]),
                data_quality=str(row["data_quality"]),
                data_source_note=row.get("data_source_note"),
            )
        )
    return {code: tuple(options) for code, options in grouped.items()}


def _fruits() -> list[RecommendationFruit]:
    dataset = load_seed_dataset()
    rows = dataset.fruits
    fruit_ids = {row.code: index for index, row in enumerate(rows, start=1)}
    options = _selection_options_by_fruit(fruit_ids)
    nutritions = {
        row.fruit_name: NutritionProfile(
            energy=float(row.energy),
            vitamin_c=float(row.vitamin_c),
            fiber=float(row.fiber),
            potassium=float(row.potassium),
            folate=float(row.folate),
            carotenoids=float(row.carotenoids),
        )
        for row in dataset.nutritions
    }
    seasons: dict[str, list[SeasonWindow]] = {}
    for row in dataset.seasons:
        seasons.setdefault(row.fruit_name, []).append(
            SeasonWindow(
                region=row.region,
                start_month=row.start_month,
                end_month=row.end_month,
                season_score=float(row.season_score),
                region_level=row.region_level,
                availability_score=float(row.availability_score),
                supply_status=row.supply_status,
            )
        )
    fruits = []
    for row in rows:
        code = row.code
        fruits.append(
            RecommendationFruit(
                id=fruit_ids[code],
                name=row.name,
                code=code,
                aliases=tuple(row.aliases),
                category=row.category,
                display_group=row.display_group or row.category,
                taste=row.taste,
                sweet_score=float(row.sweet_score),
                sour_score=float(row.sour_score),
                soft_score=float(row.soft_score),
                crisp_score=float(row.crisp_score),
                convenience_score=float(row.convenience_score),
                average_price_level=row.average_price_level,
                default_portion_grams=float(row.default_portion_grams),
                direct_eating=row.direct_eating,
                consumption_mode=row.consumption_mode,
                daily_recommendation_role=row.daily_recommendation_role,
                preparation_difficulty=float(row.preparation_difficulty),
                portability_score=float(row.portability_score),
                messiness_score=float(row.messiness_score),
                storage_difficulty=float(row.storage_difficulty),
                aroma_intensity=float(row.aroma_intensity),
                commonness_score=float(row.commonness_score),
                novelty_level=row.novelty_level,
                data_quality=row.data_quality,
                data_source_note=row.data_source_note,
                is_active=row.is_active,
                nutrition=nutritions[row.name],
                texture_score=float(row.texture_score),
                ripe_storage_score=float(row.ripe_storage_score),
                typical_purchase_stage=row.typical_purchase_stage,
                ripening_note=row.ripening_note,
                seasons=tuple(seasons[row.name]),
                selection_options=options.get(code, ()),
            )
        )
    return fruits


def _user(**changes: object) -> RecommendationUser:
    values: dict[str, object] = {
        "region": "华东",
        "sweet_preference": None,
        "sour_preference": None,
        "soft_preference": None,
        "crisp_preference": None,
        "texture_preference": None,
        "price_level": 2,
        "convenience_preference": 0.5,
        "discovery_level": 1,
    }
    values.update(changes)
    return RecommendationUser(**values)


def fixed_profiles() -> dict[str, RecommendationUser]:
    return {
        "biased_sweet_crisp": _user(sweet_preference=0.9, texture_preference=0.9),
        "sweet_soft": _user(sweet_preference=0.9, texture_preference=0.1),
        "sour_crisp": _user(sour_preference=0.9, texture_preference=0.9),
        "sour_soft": _user(sour_preference=0.9, texture_preference=0.1),
        "high_sweet_sour": _user(sweet_preference=0.9, sour_preference=0.9),
        "sweet_only": _user(sweet_preference=0.9),
        "texture_only": _user(texture_preference=0.9),
        "sour_only": _user(sour_preference=0.9),
        "no_sensory": _user(),
        "migrated_consistent": _user(soft_preference=0.2, crisp_preference=0.8),
        "migrated_conflict": _user(soft_preference=0.1, crisp_preference=0.1),
    }


def legacy_user(user: RecommendationUser) -> RecommendationUser:
    """Express the same synthetic profile with the v1 soft/crisp contract."""

    if user.texture_preference is None:
        return user
    return replace(
        user,
        soft_preference=1 - user.texture_preference,
        crisp_preference=user.texture_preference,
        texture_preference=None,
    )


def comparison_context() -> RecommendationContext:
    return RecommendationContext(
        month=7,
        today=date(2026, 8, 4),
        random_seed=20260804,
    )


def _ranking_snapshot(scored: list[object]) -> list[list[object]]:
    return [
        [
            item.fruit.id,
            (
                item.resolved_candidate.resolved_option_code
                if item.resolved_candidate is not None
                else None
            ),
        ]
        for item in scored
    ]


def _combination_snapshot(result: object) -> list[dict[str, object]]:
    return [
        {
            "rank": item.rank,
            "fruit_id": item.fruit.id,
            "fruit_code": item.fruit.code,
            "resolved_option_code": (
                item.resolved_candidate.resolved_option_code
                if item.resolved_candidate is not None
                else None
            ),
            "individual_score": round(item.individual_score, 6),
            "pair_score": round(item.pair_score, 6),
            "nutrition_pair_score": round(item.nutrition_pair_score, 6),
            "reasons": [
                reason.model_dump(mode="json") for reason in item.reasons
            ],
        }
        for item in sorted(result.items, key=lambda value: value.rank)
    ]


def _load_v1_baseline() -> dict[str, dict[str, object]]:
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != BASELINE_SCHEMA_VERSION:
        raise RuntimeError("v1 audit baseline schema version is invalid")
    if payload.get("source_revision") != V1_SOURCE_REVISION:
        raise RuntimeError("v1 audit baseline source revision is invalid")
    if payload.get("source_scoring_model") != "taste-v1":
        raise RuntimeError("v1 audit baseline scoring model is invalid")
    if payload.get("generation_contract") != BASELINE_GENERATION_CONTRACT:
        raise RuntimeError("v1 audit baseline generation contract is invalid")
    if payload.get("comparison_scope") != COMPARISON_SCOPE:
        raise RuntimeError("v1 audit baseline scope does not match the current report")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or tuple(profiles) != PROFILE_NAMES:
        raise RuntimeError("v1 audit baseline profiles are incomplete or reordered")
    required = {"ranking", "combination", "final_top2", "reason_count"}
    if any(not required <= set(profile) for profile in profiles.values()):
        raise RuntimeError("v1 audit baseline profile evidence is incomplete")
    return profiles


def build_report() -> dict[str, object]:
    fruits = _fruits()
    profiles = fixed_profiles()
    baseline = _load_v1_baseline()
    context = comparison_context()
    report: dict[str, object] = {}
    for name in PROFILE_NAMES:
        user = profiles[name]
        scored = score_candidates(fruits, user, context)
        selection = select_recommendation_pair(fruits, user, context)
        result = recommend_fruits(fruits, user, context)
        top_score = scored[0].base_score
        pair = [
            item.fruit.id
            for item in sorted(result.items, key=lambda item: item.rank)
        ]
        similarities = [item.scores.taste_match for item in scored]
        v1 = baseline[name]
        report[name] = {
            **{f"v1_{key}": value for key, value in v1.items()},
            "v2_taste_similarity_mean": round(mean(similarities), 6),
            "v2_taste_similarity_std": round(pstdev(similarities), 6),
            "v2_rank1_rank2_gap": round(
                scored[0].base_score - scored[1].base_score, 6
            ),
            "v2_single_near_top_count": sum(
                1
                for item in scored
                if top_score - item.base_score <= AUDIT_SINGLE_NEAR_TOP_THRESHOLD
            ),
            "v2_pair_near_top_count": selection.near_top_count,
            "v2_final_top2": pair,
            "v2_reason_count": sum(len(item.reasons) for item in result.items),
            "v2_ranking": _ranking_snapshot(scored),
            "v2_combination": _combination_snapshot(result),
            "recommendation_changed": v1["final_top2"] != pair,
            "comparison_scope": COMPARISON_SCOPE,
            "audit_single_near_top_threshold": AUDIT_SINGLE_NEAR_TOP_THRESHOLD,
            "production_pair_near_top_threshold": PAIR_NEAR_TOP_THRESHOLD,
        }
    return report


def build_audit_report() -> dict[str, object]:
    profiles = build_report()
    changed_count = sum(
        bool(profile["recommendation_changed"])
        for profile in profiles.values()
    )
    return {
        "comparison_label": COMPARISON_LABEL,
        "comparison_scope": COMPARISON_SCOPE,
        "profile_count": len(profiles),
        "ordered_recommendation_change_count": changed_count,
        "ordered_recommendation_change_rate": round(
            changed_count / len(profiles),
            6,
        ),
        "profiles": profiles,
    }


def main() -> int:
    print(
        json.dumps(
            build_audit_report(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
