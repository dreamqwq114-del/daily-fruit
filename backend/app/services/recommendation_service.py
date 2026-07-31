from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from itertools import combinations

from app.schemas.recommendation import (
    ReasonCode,
    ReasonComponent,
    RecommendationReason,
)
from app.services.recommendation_types import (
    FeedbackEvent,
    FruitPreference,
    HistoryEvent,
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


MISSING_SEASON_SCORE = 0.35
NUTRITION_FEATURES = (
    "energy",
    "vitamin_c",
    "fiber",
    "potassium",
    "folate",
    "carotenoids",
)
NUTRITION_PAIR_FEATURES = (
    "vitamin_c",
    "fiber",
    "potassium",
    "folate",
    "carotenoids",
)
BASE_SCORE_WEIGHTS = {
    "explicit_preference": 0.30,
    "taste_match": 0.25,
    "availability_and_season": 0.20,
    "price_match_score": 0.10,
    "convenience_score": 0.10,
    "history_diversity_score": 0.05,
}
PAIR_SCORE_WEIGHTS = {
    "individual_mean": 0.70,
    "nutrition_pair": 0.15,
    "sensory_category_diversity": 0.10,
    "pair_novelty": 0.05,
}
FEEDBACK_ADJUSTMENTS = {
    "liked": 0.08,
    "eaten": 0.0,
    "disliked": -0.12,
    "unavailable": -0.12,
    "expensive": -0.10,
    "tired_of_it": -0.10,
    "change_requested": 0.0,
    "never_tried": 0.0,
}
FEEDBACK_DECAY_DAYS = {
    "liked": 120.0,
    "disliked": 180.0,
    "unavailable": 7.0,
    "expensive": 14.0,
    "tired_of_it": 10.0,
}
MIN_FEEDBACK_ADJUSTMENT = -0.15
MAX_FEEDBACK_ADJUSTMENT = 0.15
PAIR_NEAR_TOP_THRESHOLD = 0.03
EXPLORATION_COLD_START_PENALTY = 0.08
HISTORY_SHOWN_WEIGHT = 0.12
HISTORY_EATEN_WEIGHT = 0.18
HISTORY_SHOWN_TAU_DAYS = 7.0
HISTORY_EATEN_TAU_DAYS = 10.0


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


def _region_rank(window: SeasonWindow, *, city: str, region: str) -> int:
    if window.region == city and window.region_level == "city":
        return 4
    if window.region == region and window.region_level == "province":
        return 3
    if window.region == region and window.region_level == "area":
        return 2
    if window.region == "全国" or window.region_level == "national":
        return 1
    # Keep old rows that did not have a level usable while preferring exact
    # user region matches over unrelated regions.
    if window.region == region:
        return 2
    return 0


def evaluate_season(
    seasons: Iterable[SeasonWindow],
    *,
    region: str,
    month: int,
    city: str = "",
) -> SeasonEvaluation:
    if not region.strip():
        raise InvalidRecommendationInputError("地区不能为空")
    if not 1 <= month <= 12:
        raise InvalidRecommendationInputError("月份必须在 1 到 12 之间")

    relevant: list[tuple[int, SeasonWindow]] = []
    for season in seasons:
        if not season.region.strip():
            raise InvalidRecommendationInputError("季节地区不能为空")
        if not 1 <= season.start_month <= 12 or not 1 <= season.end_month <= 12:
            raise InvalidRecommendationInputError("季节月份必须在 1 到 12 之间")
        _validate_unit_scores(
            {
                "season_score": season.season_score,
                "availability_score": season.availability_score,
            }
        )
        if season.supply_status not in {"available", "unknown", "unavailable"}:
            raise InvalidRecommendationInputError("供应状态无效")
        rank = _region_rank(season, city=city, region=region)
        if rank:
            relevant.append((rank, season))

    if not relevant:
        return SeasonEvaluation(
            score=MISSING_SEASON_SCORE,
            has_relevant_data=False,
            is_in_season=False,
            availability_score=0.45,
            supply_status="unknown",
        )

    best_rank = max(rank for rank, _ in relevant)
    specific = [season for rank, season in relevant if rank == best_rank]
    matching = [
        season
        for season in specific
        if month_is_in_range(month, season.start_month, season.end_month)
    ]
    selected = max(
        matching or specific,
        key=lambda season: (season.season_score, season.availability_score),
    )
    return SeasonEvaluation(
        score=float(selected.season_score) if matching else 0.0,
        has_relevant_data=True,
        is_in_season=bool(matching),
        availability_score=float(selected.availability_score),
        supply_status=selected.supply_status,
        region_rank=best_rank,
    )


def _portion_value(value: float | None, portion_grams: float) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise InvalidRecommendationInputError("营养字段必须是非负有限数值")
    return numeric * portion_grams / 100.0


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        raise InvalidRecommendationInputError("营养归一化缺少有效数据")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def normalize_nutrition_profiles(
    fruits: Iterable[RecommendationFruit],
) -> dict[int, NutritionProfile]:
    """Normalize against the complete supplied active library, not candidates."""
    fruit_list = list(fruits)
    fruit_ids = [fruit.id for fruit in fruit_list]
    if any(fruit_id <= 0 for fruit_id in fruit_ids):
        raise InvalidRecommendationInputError("水果 ID 必须为正整数")
    if len(fruit_ids) != len(set(fruit_ids)):
        raise InvalidRecommendationInputError("水果 ID 不能重复")

    ranges: dict[str, tuple[float, float]] = {}
    for feature in NUTRITION_FEATURES:
        values = [
            value
            for fruit in fruit_list
            for value in [
                _portion_value(
                    getattr(fruit.nutrition, feature, None)
                    if fruit.nutrition is not None
                    else None,
                    fruit.default_portion_grams,
                )
            ]
            if value is not None
        ]
        if values:
            low = _quantile(values, 0.05)
            high = _quantile(values, 0.95)
        else:
            low, high = 0.0, 0.0
        ranges[feature] = (low, high)

    normalized: dict[int, NutritionProfile] = {}
    for fruit in fruit_list:
        values: dict[str, float | None] = {}
        for feature in NUTRITION_FEATURES:
            raw = _portion_value(
                getattr(fruit.nutrition, feature, None)
                if fruit.nutrition is not None
                else None,
                fruit.default_portion_grams,
            )
            if raw is None:
                values[feature] = None
                continue
            low, high = ranges[feature]
            values[feature] = (
                0.5
                if math.isclose(low, high)
                else clamp_score((raw - low) / (high - low))
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
        if fruit.daily_recommendation_role == "supporting" and not context.allow_supporting:
            continue
        preference = user.fruit_preferences.get(fruit.id)
        if preference is not None:
            if preference.is_forbidden:
                continue
            if preference.willing_to_try is False:
                continue
            if context.exclude_disliked and math.isclose(
                float(preference.preference_score or 0), -1.0
            ):
                continue
            if user.discovery_level == 0 and preference.has_tried is False:
                continue

        season = evaluate_season(
            fruit.seasons,
            region=user.region,
            city=user.city,
            month=context.month,
        )
        if season.supply_status == "unavailable":
            continue
        eligible.append(fruit)
    return sorted(eligible, key=lambda fruit: fruit.id)


def score_candidates(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> list[ScoredFruit]:
    fruit_list = list(fruits)
    eligible = filter_eligible_fruits(fruit_list, user, context)
    if len(eligible) < 2:
        raise NoRecommendationCandidatesError(
            "符合当前条件的水果不足两种，请调整禁忌、熟悉度或地区设置"
        )
    normalized = normalize_nutrition_profiles(
        [fruit for fruit in fruit_list if fruit.is_active]
    )
    scored = [
        _score_fruit(
            fruit,
            user,
            context,
            normalized.get(fruit.id, NutritionProfile()),
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
    return clamp_score(total + scores.feedback_adjustment)


def _nutrition_values(
    profile: NutritionProfile,
    features: Iterable[str],
) -> list[float]:
    return [
        float(value)
        for feature in features
        if (value := getattr(profile, feature, None)) is not None
    ]


def nutrition_complement_score(
    first: NutritionProfile,
    second: NutritionProfile,
) -> float:
    """Backward-compatible name for the V2 nutrition pair score."""
    pairs = [
        (getattr(first, feature, None), getattr(second, feature, None))
        for feature in NUTRITION_PAIR_FEATURES
    ]
    known = [(float(left), float(right)) for left, right in pairs if left is not None and right is not None]
    if not known:
        return 0.0
    coverage = sum(max(left, right) for left, right in known) / len(known)
    diversity = sum(abs(left - right) for left, right in known) / len(known)
    confidence = len(known) / len(NUTRITION_PAIR_FEATURES)
    return clamp_score((0.75 * coverage + 0.25 * diversity) * confidence)


def _pair_novelty(
    first_id: int,
    second_id: int,
    context: RecommendationContext,
) -> float:
    pair = frozenset({first_id, second_id})
    if context.excluded_pair is not None and pair == context.excluded_pair:
        return 0.0
    if pair in context.previous_pairs:
        return 0.35
    recent = {event.fruit_id for event in context.history_events}
    if not recent:
        recent = set(context.recent_fruit_ids)
    return 0.72 if {first_id, second_id} & recent else 1.0


def _sensory_category_diversity(
    first: RecommendationFruit,
    second: RecommendationFruit,
) -> float:
    category_difference = 1.0 if first.category != second.category else 0.0
    mode_difference = 1.0 if first.consumption_mode != second.consumption_mode else 0.0
    taste_distance = sum(
        abs(getattr(first, dimension) - getattr(second, dimension))
        for dimension in ("sweet_score", "sour_score", "soft_score", "crisp_score")
    ) / 4
    return clamp_score(0.4 * category_difference + 0.3 * mode_difference + 0.3 * taste_distance)


def _pair_is_legal(
    first: RecommendationFruit,
    second: RecommendationFruit,
    user: RecommendationUser,
    context: RecommendationContext,
    scored: list[ScoredFruit],
) -> bool:
    pair = frozenset({first.id, second.id})
    if context.excluded_pair is not None and pair == context.excluded_pair:
        return False
    preferences = user.fruit_preferences
    pair_preferences = [preferences.get(first.id), preferences.get(second.id)]
    explicit_untried = [
        preference
        for preference in pair_preferences
        if preference is not None and preference.has_tried is False
    ]
    if user.discovery_level == 0 and explicit_untried:
        return False
    if user.discovery_level in {1, 2} and len(explicit_untried) > 1:
        return False
    known_tried_exists = any(
        preference is not None and preference.has_tried is True
        for item in scored
        for preference in [preferences.get(item.fruit.id)]
    )
    if user.discovery_level == 1 and known_tried_exists and not any(
        preference is not None and preference.has_tried is True
        for preference in pair_preferences
    ):
        return False
    if user.discovery_level == 2 and len(explicit_untried) == 2:
        return False
    return True


def select_recommendation_pair(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> PairSelection:
    fruit_list = list(fruits)
    scored = score_candidates(fruit_list, user, context)
    normalized = normalize_nutrition_profiles(
        [fruit for fruit in fruit_list if fruit.is_active]
    )
    pairs: list[tuple[float, float, float, float, ScoredFruit, ScoredFruit]] = []
    for first, second in combinations(scored, 2):
        if not _pair_is_legal(first.fruit, second.fruit, user, context, scored):
            continue
        nutrition_pair = nutrition_complement_score(
            normalized.get(first.fruit.id, NutritionProfile()),
            normalized.get(second.fruit.id, NutritionProfile()),
        )
        sensory = _sensory_category_diversity(first.fruit, second.fruit)
        novelty = _pair_novelty(first.fruit.id, second.fruit.id, context)
        pair_score = clamp_score(
            PAIR_SCORE_WEIGHTS["individual_mean"]
            * ((first.base_score + second.base_score) / 2)
            + PAIR_SCORE_WEIGHTS["nutrition_pair"] * nutrition_pair
            + PAIR_SCORE_WEIGHTS["sensory_category_diversity"] * sensory
            + PAIR_SCORE_WEIGHTS["pair_novelty"] * novelty
        )
        pairs.append((pair_score, nutrition_pair, sensory, novelty, first, second))
    if not pairs:
        raise NoRecommendationCandidatesError(
            "没有满足熟悉度和可推荐规则的水果组合，请调整尝鲜设置"
        )
    pairs.sort(
        key=lambda item: (
            -item[0],
            min(item[4].fruit.id, item[5].fruit.id),
            max(item[4].fruit.id, item[5].fruit.id),
        )
    )
    best_score = pairs[0][0]
    near_top = [pair for pair in pairs if best_score - pair[0] <= PAIR_NEAR_TOP_THRESHOLD]
    selected = (
        random.Random(context.random_seed).choice(near_top)
        if context.random_seed is not None
        else near_top[0]
    )
    pair_score, nutrition_pair, sensory, novelty, left, right = selected
    first, second = sorted(
        (left, right),
        key=lambda item: (-item.base_score, item.fruit.id),
    )
    return PairSelection(
        first=first,
        second=second,
        second_score=second.base_score,
        complement_score=nutrition_pair,
        pair_score=pair_score,
        nutrition_pair_score=nutrition_pair,
        sensory_category_diversity=sensory,
        pair_novelty=novelty,
    )


def recommend_fruits(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> RecommendationResult:
    selection = select_recommendation_pair(fruits, user, context)
    first_reasons = _build_reasons(selection.first, user, selection)
    second_reasons = _build_reasons(selection.second, user, selection)
    first_item = RecommendationItemResult(
        fruit=selection.first.fruit,
        score=selection.first.base_score,
        rank=1,
        reasons=first_reasons,
        base_score=selection.first.base_score,
        complement_score=selection.nutrition_pair_score,
        individual_score=selection.first.base_score,
        pair_score=selection.pair_score,
        nutrition_pair_score=selection.nutrition_pair_score,
    )
    second_item = RecommendationItemResult(
        fruit=selection.second.fruit,
        score=selection.second.base_score,
        rank=2,
        reasons=second_reasons,
        base_score=selection.second.base_score,
        complement_score=selection.nutrition_pair_score,
        individual_score=selection.second.base_score,
        pair_score=selection.pair_score,
        nutrition_pair_score=selection.nutrition_pair_score,
    )
    return RecommendationResult(
        items=(first_item, second_item),
        total_score=selection.pair_score,
    )


def _build_reasons(
    scored: ScoredFruit,
    user: RecommendationUser,
    selection: PairSelection,
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
                abs(float(contribution)),
                order,
                RecommendationReason(
                    code=code,
                    message=message,
                    component=component,
                    contribution=round(
                        clamp_score(abs(float(contribution))),
                        6,
                    ),
                ),
            )
        )
        order += 1

    preference = user.fruit_preferences.get(fruit.id)
    if preference is not None and preference.has_tried is True and (preference.preference_score or 0) >= 1:
        add(
            BASE_SCORE_WEIGHTS["explicit_preference"] * scores.explicit_preference,
            ReasonCode.EXPLICIT_PREFERENCE,
            "这是你明确喜欢的水果",
            ReasonComponent.EXPLICIT_PREFERENCE,
        )
    elif preference is not None and preference.has_tried is False:
        add(
            BASE_SCORE_WEIGHTS["explicit_preference"] * scores.explicit_preference,
            ReasonCode.EXPLORATION,
            "这是你尚未尝试过的新选择",
            ReasonComponent.FAMILIARITY,
        )
    else:
        add(
            BASE_SCORE_WEIGHTS["taste_match"] * scores.taste_match,
            ReasonCode.SWEET_MATCH,
            "甜度和口感与你设置的偏好较接近",
            ReasonComponent.TASTE_MATCH,
        )

    if scores.availability_and_season >= 0.65:
        add(
            BASE_SCORE_WEIGHTS["availability_and_season"] * scores.availability_and_season,
            ReasonCode.AVAILABILITY,
            "当前月份在你所在地区较容易购买",
            ReasonComponent.AVAILABILITY_SCORE,
        )
    if scores.price_match_score >= 0.75:
        add(
            BASE_SCORE_WEIGHTS["price_match_score"] * scores.price_match_score,
            ReasonCode.PRICE_MATCH,
            "没有超过你设置的价格范围",
            ReasonComponent.PRICE_MATCH_SCORE,
        )
    if scores.convenience_score >= 0.75:
        add(
            BASE_SCORE_WEIGHTS["convenience_score"] * scores.convenience_score,
            ReasonCode.CONVENIENT,
            "处理和携带方式符合你的便利需求",
            ReasonComponent.CONVENIENCE_SCORE,
        )
    if scores.history_diversity_score >= 0.80:
        add(
            BASE_SCORE_WEIGHTS["history_diversity_score"] * scores.history_diversity_score,
            ReasonCode.HISTORY_FRESHNESS,
            "最近一段时间没有重复推荐",
            ReasonComponent.HISTORY_FRESHNESS,
        )
    if scores.feedback_adjustment > 0.02:
        add(
            scores.feedback_adjustment,
            ReasonCode.FEEDBACK_MATCH,
            "你过去的正向反馈提高了这项推荐的匹配度",
            ReasonComponent.FEEDBACK_ADJUSTMENT,
        )
    if selection.nutrition_pair_score >= 0.40:
        add(
            PAIR_SCORE_WEIGHTS["nutrition_pair"] * selection.nutrition_pair_score,
            ReasonCode.NUTRITION_COMPLEMENT,
            "两种水果组合后覆盖了不同的营养特点",
            ReasonComponent.COMPLEMENT_SCORE,
        )
    if selection.pair_novelty >= 0.80:
        add(
            PAIR_SCORE_WEIGHTS["pair_novelty"] * selection.pair_novelty,
            ReasonCode.PAIR_NOVELTY,
            "这组搭配近期没有出现过",
            ReasonComponent.PAIR_NOVELTY,
        )

    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected_entries = candidates[:4]
    positive_feedback = next(
        (item for item in candidates if item[2].code == ReasonCode.FEEDBACK_MATCH),
        None,
    )
    if positive_feedback is not None and positive_feedback not in selected_entries:
        selected_entries[-1] = positive_feedback
    selected = [item[2] for item in selected_entries]
    while len(selected) < 2:
        selected.append(
            RecommendationReason(
                code=ReasonCode.DEFAULT_MATCH,
                message="已综合你的口味、预算和近期记录",
                component=ReasonComponent.PAIR_SCORE,
                contribution=0,
            )
        )
    return tuple(selected)


def _taste_match(fruit: RecommendationFruit, user: RecommendationUser) -> float:
    dimensions = (
        (fruit.sweet_score, user.sweet_preference),
        (fruit.sour_score, user.sour_preference),
        (fruit.soft_score, user.soft_preference),
        (fruit.crisp_score, user.crisp_preference),
    )
    # The sliders describe how much the user likes a dimension, not a target
    # fruit value: low preference therefore rewards a low fruit value.
    configured = [
        target * value + (1 - target) * (1 - value)
        for value, target in dimensions
        if target is not None
    ]
    if not configured:
        return 0.5
    return clamp_score(sum(configured) / len(configured))


def _explicit_preference_score(
    fruit: RecommendationFruit,
    user: RecommendationUser,
) -> float:
    preference = user.fruit_preferences.get(fruit.id)
    if preference is None:
        return clamp_score(0.35 + 0.10 * fruit.commonness_score)
    if preference.has_tried is False:
        return clamp_score(0.35 + 0.10 * fruit.commonness_score)
    if preference.preference_score is not None:
        value = float(preference.preference_score)
        if value <= -1:
            return 0.10
        if math.isclose(value, 0):
            return 0.50
        if math.isclose(value, 1):
            return 0.80
        return 1.0
    if preference.has_tried is True:
        return 0.50
    return clamp_score(0.40 + 0.10 * fruit.commonness_score)


def _exploration_adjustment(
    fruit: RecommendationFruit,
    user: RecommendationUser,
) -> float:
    """Lower unfamiliar exploration fruits, unless the user explicitly likes one."""
    if fruit.daily_recommendation_role != "exploration":
        return 0.0
    preference = user.fruit_preferences.get(fruit.id)
    explicitly_liked = (
        preference is not None
        and preference.preference_score is not None
        and preference.preference_score >= 1
    )
    return 0.0 if explicitly_liked else EXPLORATION_COLD_START_PENALTY


def _derived_convenience(fruit: RecommendationFruit) -> float:
    return clamp_score(
        0.30 * fruit.portability_score
        + 0.25 * (1 - fruit.preparation_difficulty)
        + 0.25 * (1 - fruit.messiness_score)
        + 0.20 * (1 - fruit.storage_difficulty)
    )


def _feedback_events_for(
    fruit_id: int,
    context: RecommendationContext,
) -> list[FeedbackEvent]:
    if context.feedback_events:
        return [event for event in context.feedback_events if event.fruit_id == fruit_id]
    now = datetime.combine(context.today or date.today(), datetime.min.time(), tzinfo=UTC)
    return [
        FeedbackEvent(fruit_id, feedback_type, now)
        for feedback_type in context.feedback_by_fruit.get(fruit_id, ())
    ]


def _feedback_adjustment(
    fruit_id: int,
    context: RecommendationContext,
) -> float:
    today = context.today or date.today()
    adjustment = 0.0
    for event in _feedback_events_for(fruit_id, context):
        if event.feedback_type == "change_requested":
            continue
        if event.feedback_type not in FEEDBACK_ADJUSTMENTS:
            raise InvalidRecommendationInputError(
                f"不支持的反馈类型：{event.feedback_type}"
            )
        base = FEEDBACK_ADJUSTMENTS[event.feedback_type]
        tau = FEEDBACK_DECAY_DAYS.get(event.feedback_type)
        days = max(0.0, (today - event.occurred_at.date()).days)
        adjustment += base if tau is None or not base else base * math.exp(-days / tau)
    return min(MAX_FEEDBACK_ADJUSTMENT, max(MIN_FEEDBACK_ADJUSTMENT, adjustment))


def _history_freshness(
    fruit_id: int,
    context: RecommendationContext,
) -> float:
    today = context.today or date.today()
    events = [event for event in context.history_events if event.fruit_id == fruit_id]
    if events:
        penalty = 0.0
        for event in events:
            days = max(0, (today - event.occurred_on).days)
            penalty += HISTORY_SHOWN_WEIGHT * max(1, event.times_shown) * math.exp(-days / HISTORY_SHOWN_TAU_DAYS)
            penalty += HISTORY_EATEN_WEIGHT * max(0, event.eaten_count) * math.exp(-days / HISTORY_EATEN_TAU_DAYS)
        return clamp_score(1 - min(0.95, penalty))
    try:
        position = context.recent_fruit_ids.index(fruit_id)
    except ValueError:
        return 1.0
    return (0.0, 0.25, 0.45, 0.65)[min(position, 3)]


def _score_fruit(
    fruit: RecommendationFruit,
    user: RecommendationUser,
    context: RecommendationContext,
    nutrition: NutritionProfile,
) -> ScoredFruit:
    season = evaluate_season(
        fruit.seasons,
        region=user.region,
        city=user.city,
        month=context.month,
    )
    feedback_adjustment = _feedback_adjustment(fruit.id, context)
    explicit = clamp_score(
        _explicit_preference_score(fruit, user)
        - _exploration_adjustment(fruit, user)
    )
    taste = _taste_match(fruit, user)
    convenience = _derived_convenience(fruit)
    scores = ScoreBreakdown(
        explicit_preference=explicit,
        taste_match=taste,
        availability_and_season=clamp_score(
            0.45 * season.score + 0.55 * season.availability_score
        ),
        price_match_score=clamp_score(
            1.0
            if fruit.average_price_level <= user.price_level
            else 1.0 - 0.5 * (fruit.average_price_level - user.price_level)
        ),
        convenience_score=clamp_score(
            1 - user.convenience_preference * (1 - convenience)
        ),
        history_diversity_score=_history_freshness(fruit.id, context),
        feedback_adjustment=feedback_adjustment,
        season_score=season.score,
        availability_score=season.availability_score,
        familiarity_score=explicit,
        known_nutrition_ratio=(
            len(_nutrition_values(nutrition, NUTRITION_FEATURES))
            / len(NUTRITION_FEATURES)
        ),
        preference_score=clamp_score(
            0.55 * explicit + 0.45 * taste
        ),
    )
    return ScoredFruit(
        fruit=fruit,
        base_score=calculate_base_score(scores),
        scores=scores,
        season=season,
    )


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
    if user.discovery_level not in {0, 1, 2}:
        raise InvalidRecommendationInputError("尝鲜等级必须为 0、1 或 2")
    _validate_unit_scores(
        {
            name: value
            for name, value in {
                "sweet_preference": user.sweet_preference,
                "sour_preference": user.sour_preference,
                "soft_preference": user.soft_preference,
                "crisp_preference": user.crisp_preference,
                "convenience_preference": user.convenience_preference,
            }.items()
            if value is not None
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
            raise InvalidRecommendationInputError("水果价格等级必须在 1 到 3 之间")
        _validate_unit_scores(
            {
                "sweet_score": fruit.sweet_score,
                "sour_score": fruit.sour_score,
                "soft_score": fruit.soft_score,
                "crisp_score": fruit.crisp_score,
                "convenience_score": fruit.convenience_score,
                "preparation_difficulty": fruit.preparation_difficulty,
                "portability_score": fruit.portability_score,
                "messiness_score": fruit.messiness_score,
                "storage_difficulty": fruit.storage_difficulty,
                "aroma_intensity": fruit.aroma_intensity,
                "commonness_score": fruit.commonness_score,
            }
        )
        if fruit.default_portion_grams <= 0 or fruit.novelty_level not in {0, 1, 2}:
            raise InvalidRecommendationInputError("水果身份字段超出范围")
        if fruit.daily_recommendation_role not in {"main", "exploration", "supporting"}:
            raise InvalidRecommendationInputError("水果推荐角色无效")
    for fruit_id, preference in user.fruit_preferences.items():
        if fruit_id <= 0:
            raise InvalidRecommendationInputError("偏好水果 ID 必须为正整数")
        if preference.preference_score is not None:
            value = float(preference.preference_score)
            if not math.isfinite(value) or not -1 <= value <= 2:
                raise InvalidRecommendationInputError("水果偏好分必须在 -1 到 2 之间")
    for event in context.history_events:
        if (
            event.fruit_id <= 0
            or event.times_shown < 0
            or event.eaten_count < 0
            or event.occurred_on > (context.today or date.today())
        ):
            raise InvalidRecommendationInputError("历史事件无效")
    valid_feedback_types = set(FEEDBACK_ADJUSTMENTS)
    for event in context.feedback_events:
        if (
            event.fruit_id <= 0
            or event.feedback_type not in valid_feedback_types
            or event.occurred_at.tzinfo is None
            or event.occurred_at.date() > (context.today or date.today())
        ):
            raise InvalidRecommendationInputError("反馈事件无效")
    if any(fruit_id <= 0 for fruit_id in context.recent_fruit_ids):
        raise InvalidRecommendationInputError("历史水果 ID 必须为正整数")
    if any(fruit_id <= 0 for fruit_id in context.feedback_by_fruit):
        raise InvalidRecommendationInputError("反馈水果 ID 必须为正整数")


def _validate_unit_scores(values: Mapping[str, float | None]) -> None:
    for name, value in values.items():
        if value is None:
            continue
        numeric = float(value)
        if not math.isfinite(numeric) or not 0 <= numeric <= 1:
            raise InvalidRecommendationInputError(f"{name} 必须在 0 到 1 之间")


__all__ = [
    "BASE_SCORE_WEIGHTS",
    "FEEDBACK_ADJUSTMENTS",
    "EXPLORATION_COLD_START_PENALTY",
    "InvalidRecommendationInputError",
    "MISSING_SEASON_SCORE",
    "NUTRITION_FEATURES",
    "NoRecommendationCandidatesError",
    "PAIR_NEAR_TOP_THRESHOLD",
    "RecommendationError",
    "calculate_base_score",
    "clamp_score",
    "evaluate_season",
    "filter_eligible_fruits",
    "month_is_in_range",
    "normalize_nutrition_profiles",
    "nutrition_complement_score",
    "recommend_fruits",
    "score_candidates",
    "select_recommendation_pair",
]
