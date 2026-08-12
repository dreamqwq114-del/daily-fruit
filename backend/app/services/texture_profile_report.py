"""Deterministic fixed-profile comparison for the texture-v2 rollout.

The checked-in v1 artifact is reproducibly replayed from ``V1_SOURCE_REVISION``
by :mod:`app.services.texture_baseline_replay`; it is not accepted merely
because its JSON metadata names that revision.  The v2 side runs the current
production core with the same seed catalog, scenario contract and time anchor.
This is a synthetic regression audit, not a claim about production-user change
rates or real-world recommendation quality.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import mean, pstdev

from app.seed.seed_fruits import load_seed_dataset
from app.services.recommendation_core.fruit_evaluation import BASE_SCORE_WEIGHTS
from app.services.recommendation_core.pair_selection import (
    PAIR_NEAR_TOP_THRESHOLD,
    PAIR_SCORE_WEIGHTS,
    select_recommendation_pair,
)
from app.services.recommendation_service import recommend_fruits, score_candidates
from app.services.recommendation_types import (
    FeedbackEvent,
    FruitPreference,
    HistoryEvent,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    NutritionProfile,
    SeasonWindow,
    SelectionOption,
)


ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = ROOT / "data" / "recommendation_v1_audit_baseline.json"
BASELINE_SCHEMA_VERSION = 2
V1_SOURCE_REVISION = "e942a72db148b7b3e30a6d21f04d9f7f99104914"
BASELINE_GENERATION_CONTRACT = "full_seed_catalog_ordered_ranking_pair_and_reasons"
AUDIT_SINGLE_NEAR_TOP_THRESHOLD = 0.02
COMPARISON_SCOPE = "fixed_synthetic_profiles_and_business_counterexamples"
COMPARISON_LABEL = "固定合成画像与业务反例对比"
COMPARISON_TODAY = date(2026, 7, 31)
COMPARISON_MONTH = COMPARISON_TODAY.month
COMPARISON_RANDOM_SEED = 20260731
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
    "low_budget",
    "high_convenience",
    "explicit_dislike_mango",
    "forbidden_mango",
    "refuses_untried_durian",
    "unavailable_mango",
    "recent_repeat_mango",
    "negative_feedback_mango",
)
HARD_EXCLUSION_TARGETS = {
    "explicit_dislike_mango": "mango",
    "forbidden_mango": "mango",
    "refuses_untried_durian": "durian",
    "unavailable_mango": "mango",
}
SOFT_PENALTY_TARGETS = {
    "recent_repeat_mango": "mango",
    "negative_feedback_mango": "mango",
}


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


def _fruit_id_by_code() -> dict[str, int]:
    return {
        row.code: index
        for index, row in enumerate(load_seed_dataset().fruits, start=1)
    }


def fixed_profiles() -> dict[str, RecommendationUser]:
    fruit_ids = _fruit_id_by_code()
    mango_id = fruit_ids["mango"]
    durian_id = fruit_ids["durian"]
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
        # Keep these two counterprofiles single-variable so a regression can
        # be attributed to the intended price or convenience input.
        "low_budget": _user(price_level=1),
        "high_convenience": _user(convenience_preference=1.0),
        "explicit_dislike_mango": _user(
            fruit_preferences={
                mango_id: FruitPreference(
                    preference_score=-1,
                    has_tried=True,
                )
            }
        ),
        "forbidden_mango": _user(
            fruit_preferences={mango_id: FruitPreference(is_forbidden=True)}
        ),
        "refuses_untried_durian": _user(
            fruit_preferences={
                durian_id: FruitPreference(
                    has_tried=False,
                    willing_to_try=False,
                )
            }
        ),
        "unavailable_mango": _user(),
        "recent_repeat_mango": _user(),
        "negative_feedback_mango": _user(),
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


def comparison_context(profile_name: str | None = None) -> RecommendationContext:
    mango_id = _fruit_id_by_code()["mango"]
    return RecommendationContext(
        month=COMPARISON_MONTH,
        today=COMPARISON_TODAY,
        random_seed=COMPARISON_RANDOM_SEED,
        history_events=(
            (
                HistoryEvent(
                    fruit_id=mango_id,
                    occurred_on=date(2026, 7, 29),
                    times_shown=1,
                    eaten_count=1,
                ),
            )
            if profile_name == "recent_repeat_mango"
            else ()
        ),
        feedback_events=(
            (
                FeedbackEvent(
                    fruit_id=mango_id,
                    feedback_type="disliked",
                    occurred_at=datetime(2026, 7, 29, 12, tzinfo=UTC),
                ),
            )
            if profile_name == "negative_feedback_mango"
            else ()
        ),
    )


def _fruits_for_profile(
    profile_name: str,
    fruits: list[RecommendationFruit],
) -> list[RecommendationFruit]:
    """Apply a scenario-only catalog change without mutating seed objects."""

    if profile_name != "unavailable_mango":
        return fruits
    return [
        replace(
            fruit,
            seasons=tuple(
                replace(window, supply_status="unavailable")
                for window in fruit.seasons
            ),
        )
        if fruit.code == "mango"
        else fruit
        for fruit in fruits
    ]


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


def _version_snapshot(*, use_legacy_users: bool) -> dict[str, dict[str, object]]:
    """Execute one algorithm version over the complete shared scenario set."""

    all_fruits = _fruits()
    profiles = fixed_profiles()
    snapshot: dict[str, dict[str, object]] = {}
    for name in PROFILE_NAMES:
        fruits = _fruits_for_profile(name, all_fruits)
        user = legacy_user(profiles[name]) if use_legacy_users else profiles[name]
        context = comparison_context(name)
        scored = score_candidates(fruits, user, context)
        selection = select_recommendation_pair(fruits, user, context)
        result = recommend_fruits(fruits, user, context)
        top_score = scored[0].base_score
        similarities = [item.scores.taste_match for item in scored]
        snapshot[name] = {
            "taste_similarity_mean": round(mean(similarities), 6),
            "taste_similarity_std": round(pstdev(similarities), 6),
            "rank1_rank2_gap": round(
                scored[0].base_score - scored[1].base_score, 6
            ),
            "single_near_top_count": sum(
                1
                for item in scored
                if top_score - item.base_score <= AUDIT_SINGLE_NEAR_TOP_THRESHOLD
            ),
            # The pre-switch PairSelection did not expose this diagnostic.
            # Keep it unknown in a source-faithful replay rather than patching
            # the old algorithm to manufacture historical evidence.
            "pair_near_top_count": getattr(selection, "near_top_count", None),
            "candidate_count": len(scored),
            "final_top2": [
                item.fruit.id
                for item in sorted(result.items, key=lambda item: item.rank)
            ],
            "reason_count": sum(len(item.reasons) for item in result.items),
            "ranking": _ranking_snapshot(scored),
            "ranking_scores": [
                [item.fruit.id, round(item.base_score, 6)] for item in scored
            ],
            "combination": _combination_snapshot(result),
        }
    return snapshot


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
    expected_context = {
        "today": COMPARISON_TODAY.isoformat(),
        "month": COMPARISON_MONTH,
        "random_seed": COMPARISON_RANDOM_SEED,
    }
    if payload.get("comparison_context") != expected_context:
        raise RuntimeError("v1 audit baseline time context is invalid")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != set(PROFILE_NAMES):
        raise RuntimeError("v1 audit baseline profiles are incomplete")
    required = {
        "ranking",
        "ranking_scores",
        "combination",
        "final_top2",
        "reason_count",
        "candidate_count",
    }
    if any(not required <= set(profile) for profile in profiles.values()):
        raise RuntimeError("v1 audit baseline profile evidence is incomplete")
    return profiles


def build_report() -> dict[str, object]:
    baseline = _load_v1_baseline()
    current = _version_snapshot(use_legacy_users=False)
    report: dict[str, object] = {}
    for name in PROFILE_NAMES:
        v1 = baseline[name]
        v2 = current[name]
        report[name] = {
            **{f"v1_{key}": value for key, value in v1.items()},
            **{f"v2_{key}": value for key, value in v2.items()},
            "recommendation_changed": v1["final_top2"] != v2["final_top2"],
            "comparison_scope": COMPARISON_SCOPE,
            "audit_single_near_top_threshold": AUDIT_SINGLE_NEAR_TOP_THRESHOLD,
            "production_pair_near_top_threshold": PAIR_NEAR_TOP_THRESHOLD,
        }
    return report


def _rank_for_code(profile: dict[str, object], fruit_code: str) -> int | None:
    fruit_id = _fruit_id_by_code()[fruit_code]
    return next(
        (
            index
            for index, item in enumerate(profile["v2_ranking"], start=1)
            if item[0] == fruit_id
        ),
        None,
    )


def _score_for_code(profile: dict[str, object], fruit_code: str) -> float | None:
    fruit_id = _fruit_id_by_code()[fruit_code]
    return next(
        (
            item[1]
            for item in profile["v2_ranking_scores"]
            if item[0] == fruit_id
        ),
        None,
    )


def _acceptance_checks(profiles: dict[str, object]) -> dict[str, bool]:
    checks = {
        f"{name}_hard_exclusion": _rank_for_code(profiles[name], fruit_code)
        is None
        for name, fruit_code in HARD_EXCLUSION_TARGETS.items()
    }
    control = profiles["no_sensory"]
    for name, fruit_code in SOFT_PENALTY_TARGETS.items():
        control_score = _score_for_code(control, fruit_code)
        penalized_score = _score_for_code(profiles[name], fruit_code)
        checks[f"{name}_lowers_score"] = (
            control_score is not None
            and penalized_score is not None
            and penalized_score < control_score
        )
    checks["low_budget_lowers_durian_score"] = (
        _score_for_code(profiles["low_budget"], "durian")
        < _score_for_code(control, "durian")
    )
    checks["high_convenience_lowers_pineapple_score"] = (
        _score_for_code(profiles["high_convenience"], "pineapple")
        < _score_for_code(control, "pineapple")
    )
    return checks


def _distribution_summary(profiles: dict[str, object], prefix: str) -> dict[str, object]:
    top1_counts: dict[str, int] = {}
    pair_counts: dict[str, int] = {}
    candidate_counts: list[int] = []
    id_to_code = {value: key for key, value in _fruit_id_by_code().items()}
    for profile in profiles.values():
        top2 = profile[f"{prefix}_final_top2"]
        top1 = id_to_code[top2[0]]
        pair = "+".join(id_to_code[fruit_id] for fruit_id in top2)
        top1_counts[top1] = top1_counts.get(top1, 0) + 1
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
        candidate_counts.append(profile[f"{prefix}_candidate_count"])
    return {
        "unique_top1_count": len(top1_counts),
        "unique_ordered_pair_count": len(pair_counts),
        "top1_frequency": dict(sorted(top1_counts.items())),
        "ordered_pair_frequency": dict(sorted(pair_counts.items())),
        "candidate_count_min": min(candidate_counts),
        "candidate_count_max": max(candidate_counts),
        "candidate_count_mean": round(mean(candidate_counts), 6),
        "largest_top1_share": round(max(top1_counts.values()) / len(profiles), 6),
        "largest_ordered_pair_share": round(
            max(pair_counts.values()) / len(profiles), 6
        ),
    }


def build_audit_report() -> dict[str, object]:
    # Imported lazily so the shared scenario harness can execute the pre-switch
    # revision, which did not expose this current texture-weight constant.
    from app.services.recommendation_core.common import TASTE_DIMENSION_WEIGHTS

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
        "comparison_context": {
            "today": COMPARISON_TODAY.isoformat(),
            "month": COMPARISON_MONTH,
            "random_seed": COMPARISON_RANDOM_SEED,
        },
        "formula": {
            "v1_taste_match": (
                "mean(target*value + (1-target)*(1-value)) over configured "
                "sweet, sour, soft and crisp dimensions"
            ),
            "v2_taste_match": (
                "weighted mean(1-abs(value-target)) over configured sweet, "
                "sour and texture dimensions"
            ),
            "availability_and_season": "0.45*season + 0.55*availability",
            "price_match": (
                "1 when fruit_price_level <= user_price_level; otherwise "
                "clamp(1 - 0.5*level_difference)"
            ),
            "convenience_match": (
                "clamp(1 - user_convenience_preference*(1-fruit_convenience))"
            ),
            "base_score_weights": dict(BASE_SCORE_WEIGHTS),
            "taste_dimension_weights": dict(TASTE_DIMENSION_WEIGHTS),
            "pair_score_weights": dict(PAIR_SCORE_WEIGHTS),
            "production_pair_near_top_threshold": PAIR_NEAR_TOP_THRESHOLD,
            "audit_single_near_top_threshold": AUDIT_SINGLE_NEAR_TOP_THRESHOLD,
        },
        "v1_distribution": _distribution_summary(profiles, "v1"),
        "v2_distribution": _distribution_summary(profiles, "v2"),
        "business_quality_decision": (
            "requires_review: distribution concentration is reported, not "
            "automatically accepted as recommendation quality"
        ),
        "acceptance_checks": _acceptance_checks(profiles),
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
