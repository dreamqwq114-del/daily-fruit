"""水果级候选过滤、营养处理和单水果评分。

这里把水果资料转换成可配对的 ``ScoredFruit``：先执行不可违反的候选
硬过滤，再按季节、偏好、历史、反馈、便利性和价格等软因素计算分数。
营养字段仍是 0～1 的演示指数；本模块只提供纯函数，不读取数据库或请求
外部服务。
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import replace
from datetime import UTC, date, datetime
from typing import cast

from app.services.recommendation_types import (
    FeedbackEvent,
    FruitPreference,
    HistoryEvent,
    NutritionProfile,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    ScoredFruit,
    ScoreBreakdown,
    SeasonEvaluation,
    SeasonWindow,
    ResolvedFruitCandidate,
)

from .common import (
    InvalidRecommendationInputError,
    NoRecommendationCandidatesError,
    TASTE_DIMENSION_WEIGHTS,
    _validate_unit_scores,
    clamp_score,
)
from .selection_options import resolve_fruit_candidate
from app.services.texture_preference import convert_legacy_texture_preference

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
# Deprecated compatibility export.  Exploration is now a user/fruit state and
# never changes a fruit's score by static role.
EXPLORATION_COLD_START_PENALTY = 0.0
HISTORY_SHOWN_WEIGHT = 0.12
HISTORY_EATEN_WEIGHT = 0.18
HISTORY_SHOWN_TAU_DAYS = 7.0
HISTORY_EATEN_TAU_DAYS = 10.0


def month_is_in_range(month: int, start_month: int, end_month: int) -> bool:
    """判断普通或跨年月份窗口是否包含当前月份。"""

    for value in (month, start_month, end_month):
        if not 1 <= value <= 12:
            raise InvalidRecommendationInputError("月份必须在 1 到 12 之间")
    if start_month <= end_month:
        return start_month <= month <= end_month
    return month >= start_month or month <= end_month


def _region_rank(window: SeasonWindow, *, city: str, region: str) -> int:
    """把季节记录映射为当前实现使用的地区优先级。

    当前顺序是 city=4、province=3、area=2、national=1；没有明确
    ``region_level`` 的旧行会按地区文本做较低优先级兼容。这里先决定
    最高地区层级，月份是否命中在 ``evaluate_season`` 的下一步判断，
    因而“更具体但当月不命中”的记录不会自动退回更宽泛层级。
    """
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
    """按城市/地区/全国优先级选择季节窗口；缺失数据只降分。

    先筛出可匹配的地区记录，再取最高层级；在该层级内优先月份命中的
    窗口，并按 ``season_score``、``availability_score`` 选最高者。已有
    记录但当月不命中时返回 ``score=0``、``is_in_season=False``；完全没有
    相关记录时返回 ``MISSING_SEASON_SCORE`` 和 ``supply_status=unknown``。
    ``unavailable`` 与 off-season 不同：前者由候选过滤硬排除，后者仍可
    进入评分，只是季节分为 0。
    """

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

    # 当前实现先按地区层级取最高 rank，再在该层级内看月份；这是稳定的
    # 地区优先策略，但也意味着城市记录不命中月份时不会回退到省/区域记录。
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

def _nutrition_index_value(value: float | None) -> float | None:
    """校验并返回一个 0～1 的演示营养指数，保留缺失值。

    ``nutrition_demo.csv`` 保存的是已经归一化的相对特征，不是每 100 克的
    真实营养含量，因此这里不能再使用建议份量进行换算。
    """
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric) or not 0 <= numeric <= 1:
        raise InvalidRecommendationInputError(
            "演示营养指数必须在 0 到 1 之间"
        )
    return numeric


def _quantile(values: list[float], probability: float) -> float:
    """计算归一化所需的线性插值分位点；空集合是输入错误。"""
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
    """在完整 active 水果库上做 P05/P95 归一化，而不是只看候选集。

    演示 CSV 已经保存 0～1 的无物理单位相对特征，
    ``default_portion_grams`` 在当前方案中不参与营养计算。
    """
    # 归一化基准使用完整 active 水果库，而不是已经被用户偏好裁剪后的
    # 候选集，避免同一水果因用户画像变化而改变其相对营养分数。
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
                _nutrition_index_value(
                    getattr(fruit.nutrition, feature, None)
                    if fruit.nutrition is not None
                    else None,
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
            raw = _nutrition_index_value(
                getattr(fruit.nutrition, feature, None)
                if fruit.nutrition is not None
                else None,
            )
            # 缺失营养不会被伪造成 0 或 0.5；pair 评分会用 known coverage
            # 单独表达“有多少维度有数据”。
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
    """执行评分前的硬过滤。

    ``inactive``、supporting 角色（除非上下文显式允许）、forbidden、
    ``willing_to_try=False``、配置启用的明确不喜欢、保守模式下明确没吃过，
    以及供应状态 ``unavailable`` 会在评分前被移除。硬约束不能只靠降分，
    否则候选不足或其它水果分数更低时仍可能回到最终组合。当前代码并未
    把 ``has_tried=None`` 当成没吃过，也没有读取购买条件字段。
    """

    fruit_list = list(fruits)
    _validate_inputs(fruit_list, user, context)
    return [
        fruit
        for fruit, _ in _eligible_resolved_fruits(fruit_list, user, context)
    ]


def _eligible_resolved_fruits(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> list[tuple[RecommendationFruit, ResolvedFruitCandidate]]:
    """过滤并解析父水果；同一轮每个父水果只解析一次。"""

    fruit_list = list(fruits)
    eligible: list[tuple[RecommendationFruit, ResolvedFruitCandidate]] = []
    # 先做硬过滤，再让后续 score_candidates 处理软偏好；排序只为保证
    # 没有随机 seed 时的 tie-break 稳定，不代表这里已经完成最终排名。
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

        resolution_user = user
        if (
            not context.exclude_disliked
            and preference is not None
            and preference.preference_score is not None
            and math.isclose(float(preference.preference_score), -1.0)
        ):
            # ``exclude_disliked=False`` is a public compatibility mode: a
            # disliked fruit may still be scored.  Keep that switch at the
            # filtering boundary rather than letting the option resolver
            # turn it into a hard exclusion.
            resolution_user = replace(
                user,
                fruit_preferences={
                    **user.fruit_preferences,
                    fruit.id: replace(preference, preference_score=0.0),
                },
            )

        resolved = resolve_fruit_candidate(fruit, resolution_user)
        if resolved is None:
            continue

        season = evaluate_season(
            fruit.seasons,
            region=user.region,
            city=user.city,
            month=context.month,
        )
        if season.supply_status == "unavailable":
            continue
        eligible.append((fruit, resolved))
    return sorted(eligible, key=lambda item: item[0].id)


def _score_candidates_with_normalized(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> tuple[list[ScoredFruit], dict[int, NutritionProfile]]:
    """先过滤，再把每个候选映射为可解释的 ScoreBreakdown。

    营养归一化仍基于全部 active 水果；只有过滤后的水果进入单水果评分。
    配对选择同时需要这份归一化结果，因此这里一次返回评分列表和营养档案，
    避免同一推荐流程重复执行完全相同的归一化。
    算法需要至少两个候选，候选不足会抛出领域错误而不是返回重复水果。
    """

    fruit_list = list(fruits)
    _validate_inputs(fruit_list, user, context)
    eligible = _eligible_resolved_fruits(fruit_list, user, context)
    if len(eligible) < 2:
        raise NoRecommendationCandidatesError(
            "符合当前条件的水果不足两种，请调整禁忌、熟悉度或地区设置"
        )
    normalized = normalize_nutrition_profiles(
        [fruit for fruit in fruit_list if fruit.is_active]
    )
    scored = [
        _score_fruit(
            resolved,
            user,
            context,
            normalized.get(fruit.id, NutritionProfile()),
        )
        for fruit, resolved in eligible
    ]
    return sorted(scored, key=lambda item: (-item.base_score, item.fruit.id)), normalized


def score_candidates(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> list[ScoredFruit]:
    """公开的单水果评分入口；保留原签名并丢弃内部归一化档案。"""

    scored, _ = _score_candidates_with_normalized(fruits, user, context)
    return scored


def calculate_base_score(scores: ScoreBreakdown) -> float:
    """应用集中定义的单水果权重，并叠加有界反馈调整。

    当前公式是 ``sum(weight_i * score_i) + feedback_adjustment``，结果再
    clamp 到 0～1。反馈不参与基础权重和校验，但必须受全局上下界限制；
    这样理由可以分别解释“匹配得分”和“历史反馈修正”。
    """

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
    values: list[float] = []
    for feature in features:
        # ``getattr`` 动态取属性时会被 IDEA 推断为 ``Any | None``；
        # NutritionProfile 的营养字段实际约定为 ``float | None``。
        value = cast(float | None, getattr(profile, feature, None))
        if value is not None:
            values.append(float(value))
    return values

def _taste_match_details(
    fruit: RecommendationFruit,
    user: RecommendationUser,
    resolved: ResolvedFruitCandidate | None = None,
) -> tuple[float, int, float, tuple[str, ...]]:
    if resolved is not None:
        sweet = resolved.effective_sweet_score
        sour = resolved.effective_sour_score
        texture = resolved.effective_texture_score
    else:
        sweet = fruit.sweet_score
        sour = fruit.sour_score
        texture = fruit.texture_score
    texture_target = user.texture_preference
    if texture_target is None:
        texture_target, _ = convert_legacy_texture_preference(
            user.soft_preference, user.crisp_preference
        )
    dimensions = (
        (
            "sweet_score", sweet, user.sweet_preference,
            TASTE_DIMENSION_WEIGHTS["sweet_score"],
        ),
        (
            "sour_score", sour, user.sour_preference,
            TASTE_DIMENSION_WEIGHTS["sour_score"],
        ),
        (
            "texture_score", texture, texture_target,
            TASTE_DIMENSION_WEIGHTS["texture_score"],
        ),
    )
    configured = [
        (name, 1 - abs(float(value) - float(target)), weight)
        for name, value, target, weight in dimensions
        if value is not None and target is not None
    ]
    if not configured:
        return 0.5, 0, 0.0, ()
    weight_sum = sum(weight for _, _, weight in configured)
    score = sum(match * weight for _, match, weight in configured) / weight_sum
    return clamp_score(score), len(configured), weight_sum, tuple(
        name for name, _, _ in configured
    )


def _taste_match(
    fruit: RecommendationFruit,
    user: RecommendationUser,
    resolved: ResolvedFruitCandidate | None = None,
) -> float:
    return _taste_match_details(fruit, user, resolved)[0]


def _explicit_preference_score(
    fruit: RecommendationFruit,
    user: RecommendationUser,
    resolved: ResolvedFruitCandidate | None = None,
) -> float:
    """将单水果偏好映射为 0～1 的个人匹配先验。

    当前兼容逻辑对 ``has_tried=False`` 直接使用 commonness，不读取
    ``preference_score``；其它状态只要有 preference_score 就会读取，
    因而 UNKNOWN 行若同时带有偏好分也会影响排序。这是当前实现事实，
    与“偏好分只描述已吃过水果”的理想语义并不完全一致，本任务不改动它。
    """
    if resolved is not None and resolved.option_explicitly_liked:
        # An option-level like is the single effective explicit preference;
        # parent and option likes are never added together.
        return 1.0
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


def is_exploration_recommendation(
    fruit: RecommendationFruit,
    preference: FruitPreference | None,
    user: RecommendationUser,
) -> bool:
    """Return a dynamic exploration label without changing the score.

    A missing ``has_tried`` value is unknown rather than untried.  The label is
    intentionally derived per user and fruit, so it is never persisted as a
    permanent fruit role.
    """

    del fruit  # The relationship is represented by the supplied preference.
    return bool(
        preference is not None
        and preference.has_tried is False
        and preference.willing_to_try is not False
        and preference.is_forbidden is False
        and user.discovery_level != 0
    )


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
    """优先返回带时间的反馈事件，旧聚合输入只作兼容 fallback。

    ``feedback_by_fruit`` 没有原始时间，因此 fallback 会用当天零点合成
    事件，等价于不再提供真实历史衰减信息；新调用者应传入
    ``feedback_events``。时间戳不能在每次运行时重新生成，否则同一历史
    反馈会被反复当作“刚发生”。
    """
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
    """按反馈类型和发生时间累计有界调整，不把刷新事件当长期偏好。"""
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
    """将展示/吃过历史转成 0～1 新鲜度。

    有带日期的 ``history_events`` 时按每个日期事件指数衰减；没有该水果
    的聚合事件时再使用旧的 recent_fruit_ids 位置 fallback。查询窗口之外
    的历史根本不会到达这里，因此窗口长度与 tau 不能互相替代。
    """
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
    resolved: ResolvedFruitCandidate,
    user: RecommendationUser,
    context: RecommendationContext,
    nutrition: NutritionProfile,
) -> ScoredFruit:
    """计算一个候选的全部子分数并生成可解释的单水果结果。

    ``availability_and_season`` 由 0.45*season + 0.55*availability 组成；
    convenience 先由水果自身的可携带/处理/脏乱/储存属性推导，再按用户
    convenience_preference 调整。当前基础公式不读取市场购买条件，也不把
    ``nutrition_diversity_score`` 单独加权；这些字段的存在不能被解释成已
    参与排序。
    """
    fruit = resolved.fruit
    season = evaluate_season(
        fruit.seasons,
        region=user.region,
        city=user.city,
        month=context.month,
    )
    feedback_adjustment = _feedback_adjustment(fruit.id, context)
    explicit = clamp_score(_explicit_preference_score(fruit, user, resolved))
    taste, configured_count, configured_weight_sum, configured_dimensions = (
        _taste_match_details(fruit, user, resolved)
    )
    convenience = (
        resolved.effective_convenience_score
        if resolved.effective_convenience_score is not None
        else _derived_convenience(fruit)
    )
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
        configured_dimension_count=configured_count,
        configured_weight_sum=configured_weight_sum,
        configured_dimensions=configured_dimensions,
    )
    return ScoredFruit(
        fruit=fruit,
        base_score=calculate_base_score(scores),
        scores=scores,
        season=season,
        resolved_candidate=resolved,
    )


def _validate_inputs(
    fruits: list[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> None:
    """在任何过滤/评分前验证算法边界，不负责修正业务数据。

    这里验证数值范围、ID 唯一性、角色、历史/反馈时间和反馈类型；它没有
    把 ``preference_score`` 与 ``has_tried`` 绑定，也没有把缺失营养补成
    数值。调用方应把验证失败当作输入合同错误，而不是通过降低分数继续
    生成推荐。
    """
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
                "texture_preference": user.texture_preference,
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
                "texture_score": fruit.texture_score,
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
        if fruit.daily_recommendation_role not in {"main", "supporting"}:
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
