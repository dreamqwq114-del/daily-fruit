from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from app.services.recommendation_types import (
    NutritionProfile,
    RecommendationFruit,
    SeasonEvaluation,
    SeasonWindow,
)


MISSING_SEASON_SCORE = 0.35
NUTRITION_FEATURES = (
    "energy",
    "vitamin_c",
    "fiber",
    "potassium",
    "folate",
    "carotenoids",
)


class RecommendationError(Exception):
    """Base class for understandable recommendation domain errors."""


class InvalidRecommendationInputError(RecommendationError):
    """Raised when data passed to the pure algorithm is invalid."""


class NoRecommendationCandidatesError(RecommendationError):
    """Raised when fewer than two eligible fruits remain."""


def clamp_score(value: float) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidRecommendationInputError("分数必须是有限数值")
    return min(1.0, max(0.0, numeric))


def month_is_in_range(month: int, start_month: int, end_month: int) -> bool:
    for value in (month, start_month, end_month):
        if not 1 <= value <= 12:
            raise InvalidRecommendationInputError("月份必须在 1 到 12 之间")

    if start_month <= end_month:
        return start_month <= month <= end_month
    return month >= start_month or month <= end_month


def evaluate_season(
    seasons: Iterable[SeasonWindow],
    *,
    region: str,
    month: int,
) -> SeasonEvaluation:
    if not region.strip():
        raise InvalidRecommendationInputError("地区不能为空")
    if not 1 <= month <= 12:
        raise InvalidRecommendationInputError("月份必须在 1 到 12 之间")

    relevant = [
        season
        for season in seasons
        if season.region in {region, "全国"}
    ]
    if not relevant:
        return SeasonEvaluation(
            score=MISSING_SEASON_SCORE,
            has_relevant_data=False,
            is_in_season=False,
        )

    matching = [
        season
        for season in relevant
        if month_is_in_range(
            month,
            season.start_month,
            season.end_month,
        )
    ]
    if not matching:
        return SeasonEvaluation(
            score=0.0,
            has_relevant_data=True,
            is_in_season=False,
        )

    return SeasonEvaluation(
        score=max(clamp_score(season.season_score) for season in matching),
        has_relevant_data=True,
        is_in_season=True,
    )


def normalize_nutrition_profiles(
    fruits: Iterable[RecommendationFruit],
) -> dict[int, NutritionProfile]:
    fruit_list = list(fruits)
    fruit_ids = [fruit.id for fruit in fruit_list]
    if any(fruit_id <= 0 for fruit_id in fruit_ids):
        raise InvalidRecommendationInputError("水果 ID 必须为正整数")
    if len(fruit_ids) != len(set(fruit_ids)):
        raise InvalidRecommendationInputError("水果 ID 不能重复")

    known_profiles = [
        fruit.nutrition
        for fruit in fruit_list
        if fruit.nutrition is not None
    ]
    feature_ranges: dict[str, tuple[float, float]] = {}
    for feature in NUTRITION_FEATURES:
        values = [
            _nonnegative_feature(profile, feature)
            for profile in known_profiles
        ]
        feature_ranges[feature] = (
            (min(values), max(values)) if values else (0.0, 0.0)
        )

    normalized: dict[int, NutritionProfile] = {}
    for fruit in fruit_list:
        values: dict[str, float] = {}
        for feature in NUTRITION_FEATURES:
            if fruit.nutrition is None:
                values[feature] = 0.5
                continue
            minimum, maximum = feature_ranges[feature]
            raw_value = _nonnegative_feature(fruit.nutrition, feature)
            values[feature] = (
                0.5
                if math.isclose(minimum, maximum)
                else (raw_value - minimum) / (maximum - minimum)
            )
        normalized[fruit.id] = NutritionProfile(**values)

    return normalized


def _nonnegative_feature(
    profile: NutritionProfile,
    feature: str,
) -> float:
    value = float(getattr(profile, feature))
    if not math.isfinite(value) or value < 0:
        raise InvalidRecommendationInputError(
            f"营养字段 {feature} 必须是非负有限数值"
        )
    return value


__all__ = [
    "InvalidRecommendationInputError",
    "MISSING_SEASON_SCORE",
    "NUTRITION_FEATURES",
    "NoRecommendationCandidatesError",
    "RecommendationError",
    "clamp_score",
    "evaluate_season",
    "month_is_in_range",
    "normalize_nutrition_profiles",
]
