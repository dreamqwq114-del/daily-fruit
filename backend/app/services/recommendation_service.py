from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping

from app.services.recommendation_types import (
    NutritionProfile,
    PairSelection,
    RecommendationContext,
    RecommendationFruit,
    RecommendationItemResult,
    RecommendationResult,
    RecommendationUser,
    ScoredFruit,
    ScoreBreakdown,
    SeasonEvaluation,
    SeasonWindow,
)
from app.schemas.recommendation import (
    ReasonCode,
    ReasonComponent,
    RecommendationReason,
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
NUTRITION_DIVERSITY_FEATURES = (
    "vitamin_c",
    "fiber",
    "potassium",
    "folate",
    "carotenoids",
)
BASE_SCORE_WEIGHTS = {
    "season_score": 0.35,
    "preference_score": 0.25,
    "nutrition_diversity_score": 0.20,
    "history_diversity_score": 0.10,
    "convenience_score": 0.05,
    "price_match_score": 0.05,
}
FEEDBACK_ADJUSTMENTS = {
    "liked": 0.15,
    "eaten": 0.05,
    "disliked": -0.25,
    "unavailable": -0.05,
    "expensive": -0.15,
    "tired_of_it": -0.25,
    "change_requested": -0.10,
}
MIN_FEEDBACK_ADJUSTMENT = -0.35
MAX_FEEDBACK_ADJUSTMENT = 0.25
NEAR_TOP_THRESHOLD = 0.02
SECOND_BASE_WEIGHT = 0.70
SECOND_COMPLEMENT_WEIGHT = 0.30


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


def filter_eligible_fruits(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> list[RecommendationFruit]:
    fruit_list = list(fruits)
    _validate_inputs(fruit_list, user, context)

    eligible: list[RecommendationFruit] = []
    for fruit in fruit_list:
        if not fruit.is_active:
            continue
        preference = user.fruit_preferences.get(fruit.id)
        if preference is not None and preference.is_forbidden:
            continue
        if (
            context.exclude_disliked
            and preference is not None
            and math.isclose(float(preference.preference_score), -1.0)
        ):
            continue

        season = evaluate_season(
            fruit.seasons,
            region=user.region,
            month=context.month,
        )
        if season.has_relevant_data and not season.is_in_season:
            continue
        eligible.append(fruit)

    return sorted(eligible, key=lambda fruit: fruit.id)


def score_candidates(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> list[ScoredFruit]:
    eligible = filter_eligible_fruits(fruits, user, context)
    if len(eligible) < 2:
        raise NoRecommendationCandidatesError(
            "符合当前条件的水果不足两种，请调整禁忌、偏好或地区设置"
        )

    normalized_nutrition = normalize_nutrition_profiles(eligible)
    scored = [
        _score_fruit(
            fruit,
            user,
            context,
            normalized_nutrition[fruit.id],
        )
        for fruit in eligible
    ]
    return sorted(scored, key=lambda item: (-item.base_score, item.fruit.id))


def calculate_base_score(scores: ScoreBreakdown) -> float:
    if not math.isclose(sum(BASE_SCORE_WEIGHTS.values()), 1.0):
        raise RuntimeError("推荐基础权重之和必须为 1")
    total = sum(
        getattr(scores, component) * weight
        for component, weight in BASE_SCORE_WEIGHTS.items()
    )
    return clamp_score(total)


def nutrition_complement_score(
    first: NutritionProfile,
    second: NutritionProfile,
) -> float:
    first_values = [float(getattr(first, name)) for name in NUTRITION_FEATURES]
    second_values = [
        float(getattr(second, name)) for name in NUTRITION_FEATURES
    ]
    _validate_unit_scores(
        {f"first_{name}": value for name, value in zip(
            NUTRITION_FEATURES,
            first_values,
            strict=True,
        )}
    )
    _validate_unit_scores(
        {f"second_{name}": value for name, value in zip(
            NUTRITION_FEATURES,
            second_values,
            strict=True,
        )}
    )

    gaps = [1.0 - value for value in first_values]
    gap_total = sum(gaps)
    coverage = (
        0.5
        if math.isclose(gap_total, 0.0)
        else sum(
            gap * candidate
            for gap, candidate in zip(gaps, second_values, strict=True)
        )
        / gap_total
    )
    contrast = sum(
        abs(candidate - selected)
        for selected, candidate in zip(
            first_values,
            second_values,
            strict=True,
        )
    ) / len(NUTRITION_FEATURES)
    return clamp_score(coverage * 0.80 + contrast * 0.20)


def select_recommendation_pair(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> PairSelection:
    scored = score_candidates(fruits, user, context)
    top_score = scored[0].base_score
    near_top = [
        item
        for item in scored
        if top_score - item.base_score <= NEAR_TOP_THRESHOLD
    ]
    first = (
        near_top[0]
        if context.random_seed is None
        else random.Random(context.random_seed).choice(near_top)
    )

    normalized = normalize_nutrition_profiles(
        item.fruit for item in scored
    )
    ranked_seconds: list[tuple[float, float, ScoredFruit]] = []
    for candidate in scored:
        if candidate.fruit.id == first.fruit.id:
            continue
        complement = nutrition_complement_score(
            normalized[first.fruit.id],
            normalized[candidate.fruit.id],
        )
        second_score = clamp_score(
            candidate.base_score * SECOND_BASE_WEIGHT
            + complement * SECOND_COMPLEMENT_WEIGHT
        )
        ranked_seconds.append((second_score, complement, candidate))

    ranked_seconds.sort(
        key=lambda item: (-item[0], item[2].fruit.id)
    )
    second_score, complement_score, second = ranked_seconds[0]
    return PairSelection(
        first=first,
        second=second,
        second_score=second_score,
        complement_score=complement_score,
    )


def recommend_fruits(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> RecommendationResult:
    selection = select_recommendation_pair(fruits, user, context)
    first_reasons = _build_reasons(
        selection.first,
        user,
        complement_score=None,
    )
    second_reasons = _build_reasons(
        selection.second,
        user,
        complement_score=selection.complement_score,
    )
    first_item = RecommendationItemResult(
        fruit=selection.first.fruit,
        score=selection.first.base_score,
        rank=1,
        reasons=first_reasons,
        base_score=selection.first.base_score,
    )
    second_item = RecommendationItemResult(
        fruit=selection.second.fruit,
        score=selection.second_score,
        rank=2,
        reasons=second_reasons,
        base_score=selection.second.base_score,
        complement_score=selection.complement_score,
    )
    return RecommendationResult(
        items=(first_item, second_item),
        total_score=clamp_score(
            (first_item.score + second_item.score) / 2
        ),
    )


def _build_reasons(
    scored: ScoredFruit,
    user: RecommendationUser,
    *,
    complement_score: float | None,
) -> tuple[RecommendationReason, ...]:
    fruit = scored.fruit
    scores = scored.scores
    candidates: list[tuple[float, int, RecommendationReason]] = []
    order = 0

    def add(
        contribution: float,
        code: ReasonCode,
        message: str,
        component: ReasonComponent,
    ) -> None:
        nonlocal order
        candidates.append(
            (
                contribution,
                order,
                RecommendationReason(
                    code=code,
                    message=message,
                    component=component,
                ),
            )
        )
        order += 1

    if complement_score is not None and complement_score >= 0.40:
        add(
            complement_score * SECOND_COMPLEMENT_WEIGHT,
            ReasonCode.NUTRITION_COMPLEMENT,
            "与另一种水果的营养特点形成互补",
            ReasonComponent.COMPLEMENT_SCORE,
        )
    if scored.season.is_in_season:
        add(
            scores.season_score * BASE_SCORE_WEIGHTS["season_score"],
            ReasonCode.IN_SEASON,
            "当前处于适宜购买月份",
            ReasonComponent.SEASON_SCORE,
        )

    if scores.feedback_adjustment > 0:
        add(
            scores.preference_score
            * BASE_SCORE_WEIGHTS["preference_score"],
            ReasonCode.FEEDBACK_MATCH,
            "你过去的正向反馈提高了这项推荐的匹配度",
            ReasonComponent.FEEDBACK_ADJUSTMENT,
        )
    else:
        taste_code, taste_message = _best_taste_reason(fruit, user)
        add(
            scores.preference_score
            * BASE_SCORE_WEIGHTS["preference_score"],
            taste_code,
            taste_message,
            ReasonComponent.PREFERENCE_SCORE,
        )

    add(
        scores.nutrition_diversity_score
        * BASE_SCORE_WEIGHTS["nutrition_diversity_score"],
        ReasonCode.NUTRITION_DIVERSITY,
        "营养特征参与了本组的多样性搭配",
        ReasonComponent.NUTRITION_DIVERSITY_SCORE,
    )
    if scores.history_diversity_score >= 0.80:
        add(
            scores.history_diversity_score
            * BASE_SCORE_WEIGHTS["history_diversity_score"],
            ReasonCode.NOT_RECENTLY_RECOMMENDED,
            "最近一段时间没有推荐过",
            ReasonComponent.HISTORY_DIVERSITY_SCORE,
        )
    if scores.price_match_score >= 0.75:
        add(
            scores.price_match_score
            * BASE_SCORE_WEIGHTS["price_match_score"],
            ReasonCode.PRICE_MATCH,
            "符合你的价格范围",
            ReasonComponent.PRICE_MATCH_SCORE,
        )
    if scores.convenience_score >= 0.75:
        add(
            scores.convenience_score
            * BASE_SCORE_WEIGHTS["convenience_score"],
            ReasonCode.CONVENIENT,
            "食用便利性符合你的偏好",
            ReasonComponent.CONVENIENCE_SCORE,
        )

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in candidates[:4])


def _best_taste_reason(
    fruit: RecommendationFruit,
    user: RecommendationUser,
) -> tuple[ReasonCode, str]:
    dimensions = (
        (
            "甜度",
            fruit.sweet_score,
            user.sweet_preference,
            ReasonCode.SWEET_MATCH,
            "符合你偏甜的口味",
        ),
        (
            "酸度",
            fruit.sour_score,
            user.sour_preference,
            ReasonCode.SOUR_MATCH,
            "符合你偏酸的口味",
        ),
        (
            "柔软度",
            fruit.soft_score,
            user.soft_preference,
            ReasonCode.SOFT_MATCH,
            "符合你偏软的口感",
        ),
        (
            "脆度",
            fruit.crisp_score,
            user.crisp_preference,
            ReasonCode.CRISP_MATCH,
            "符合你偏脆的口感",
        ),
    )
    name, fruit_value, user_value, code, positive_message = max(
        dimensions,
        key=lambda item: 1.0 - abs(item[1] - item[2]),
    )
    closeness = 1.0 - abs(fruit_value - user_value)
    if fruit_value >= 0.60 and user_value >= 0.60:
        return code, positive_message
    if closeness >= 0.60:
        return code, f"{name}特征与你设置的口味偏好较接近"
    return code, f"已按你设置的{name}偏好参与综合评分"


def _score_fruit(
    fruit: RecommendationFruit,
    user: RecommendationUser,
    context: RecommendationContext,
    nutrition: NutritionProfile,
) -> ScoredFruit:
    season = evaluate_season(
        fruit.seasons,
        region=user.region,
        month=context.month,
    )
    feedback_adjustment = _feedback_adjustment(
        context.feedback_by_fruit.get(fruit.id, ())
    )
    scores = ScoreBreakdown(
        season_score=season.score,
        preference_score=_preference_score(
            fruit,
            user,
            feedback_adjustment,
        ),
        nutrition_diversity_score=sum(
            getattr(nutrition, feature)
            for feature in NUTRITION_DIVERSITY_FEATURES
        )
        / len(NUTRITION_DIVERSITY_FEATURES),
        history_diversity_score=_history_diversity_score(
            fruit.id,
            context.recent_fruit_ids,
        ),
        convenience_score=1.0
        - abs(fruit.convenience_score - user.convenience_preference),
        price_match_score=max(
            0.0,
            1.0
            - 0.5 * abs(fruit.average_price_level - user.price_level),
        ),
        feedback_adjustment=feedback_adjustment,
    )
    return ScoredFruit(
        fruit=fruit,
        base_score=calculate_base_score(scores),
        scores=scores,
        season=season,
    )


def _preference_score(
    fruit: RecommendationFruit,
    user: RecommendationUser,
    feedback_adjustment: float,
) -> float:
    taste_similarity = 1.0 - sum(
        (
            abs(fruit.sweet_score - user.sweet_preference),
            abs(fruit.sour_score - user.sour_preference),
            abs(fruit.soft_score - user.soft_preference),
            abs(fruit.crisp_score - user.crisp_preference),
        )
    ) / 4
    preference = user.fruit_preferences.get(fruit.id)
    explicit_score = (
        0.5
        if preference is None
        else _normalize_explicit_preference(preference.preference_score)
    )
    return clamp_score(
        taste_similarity * 0.70
        + explicit_score * 0.30
        + feedback_adjustment
    )


def _normalize_explicit_preference(value: float) -> float:
    numeric = float(value)
    if numeric <= 0:
        return (numeric + 1.0) * 0.5
    return 0.5 + numeric * 0.25


def _feedback_adjustment(feedback_types: Iterable[str]) -> float:
    adjustment = 0.0
    for feedback_type in feedback_types:
        if feedback_type not in FEEDBACK_ADJUSTMENTS:
            raise InvalidRecommendationInputError(
                f"不支持的反馈类型：{feedback_type}"
            )
        adjustment += FEEDBACK_ADJUSTMENTS[feedback_type]
    return min(
        MAX_FEEDBACK_ADJUSTMENT,
        max(MIN_FEEDBACK_ADJUSTMENT, adjustment),
    )


def _history_diversity_score(
    fruit_id: int,
    recent_fruit_ids: tuple[int, ...],
) -> float:
    try:
        position = recent_fruit_ids.index(fruit_id)
    except ValueError:
        return 1.0
    if position == 0:
        return 0.0
    if position == 1:
        return 0.2
    if position == 2:
        return 0.4
    return 0.6


def _validate_inputs(
    fruits: list[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> None:
    if not 1 <= context.month <= 12:
        raise InvalidRecommendationInputError("月份必须在 1 到 12 之间")
    if not user.region.strip():
        raise InvalidRecommendationInputError("地区不能为空")
    if not 1 <= user.price_level <= 3:
        raise InvalidRecommendationInputError("用户价格等级必须在 1 到 3 之间")

    _validate_unit_scores(
        {
            "sweet_preference": user.sweet_preference,
            "sour_preference": user.sour_preference,
            "soft_preference": user.soft_preference,
            "crisp_preference": user.crisp_preference,
            "convenience_preference": user.convenience_preference,
        }
    )
    fruit_ids = [fruit.id for fruit in fruits]
    if any(fruit_id <= 0 for fruit_id in fruit_ids):
        raise InvalidRecommendationInputError("水果 ID 必须为正整数")
    if len(fruit_ids) != len(set(fruit_ids)):
        raise InvalidRecommendationInputError("水果 ID 不能重复")

    for fruit in fruits:
        if not fruit.name.strip():
            raise InvalidRecommendationInputError("水果名称不能为空")
        if not 1 <= fruit.average_price_level <= 3:
            raise InvalidRecommendationInputError(
                "水果价格等级必须在 1 到 3 之间"
            )
        _validate_unit_scores(
            {
                "sweet_score": fruit.sweet_score,
                "sour_score": fruit.sour_score,
                "soft_score": fruit.soft_score,
                "crisp_score": fruit.crisp_score,
                "convenience_score": fruit.convenience_score,
            }
        )

    for fruit_id, preference in user.fruit_preferences.items():
        if fruit_id <= 0:
            raise InvalidRecommendationInputError("偏好水果 ID 必须为正整数")
        value = float(preference.preference_score)
        if not math.isfinite(value) or not -1 <= value <= 2:
            raise InvalidRecommendationInputError(
                "水果偏好分必须在 -1 到 2 之间"
            )


def _validate_unit_scores(values: Mapping[str, float]) -> None:
    for name, value in values.items():
        numeric = float(value)
        if not math.isfinite(numeric) or not 0 <= numeric <= 1:
            raise InvalidRecommendationInputError(
                f"{name} 必须在 0 到 1 之间"
            )


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
    "BASE_SCORE_WEIGHTS",
    "FEEDBACK_ADJUSTMENTS",
    "MISSING_SEASON_SCORE",
    "NUTRITION_FEATURES",
    "NoRecommendationCandidatesError",
    "RecommendationError",
    "clamp_score",
    "calculate_base_score",
    "evaluate_season",
    "filter_eligible_fruits",
    "month_is_in_range",
    "normalize_nutrition_profiles",
    "nutrition_complement_score",
    "recommend_fruits",
    "score_candidates",
    "select_recommendation_pair",
]
