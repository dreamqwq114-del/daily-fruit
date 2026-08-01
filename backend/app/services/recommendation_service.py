"""纯 Python 水果推荐算法。

输入是 recommendation_types 中的不可变数据对象，输出是两种水果及
可解释理由；本模块不访问数据库、网络或 FastAPI。完整管线是：输入验证
→ 地区/月度季节与供应判断 → 硬过滤 → 营养归一化 → 单水果评分
→ 枚举合法水果对 → 组合评分 → 在近优组合中按 seed 选择 → 理由生成。
购买条件字段 ``market_access_level`` 和 ``accepts_online_purchase`` 没有
进入 RecommendationUser，因此当前只保存、不参与排序。注释描述的是
当前实现，不把产品理想规则写成已完成的算法行为。
"""

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
# energy 用于完整营养归一化和数据置信度；组合互补只使用下方五个特征。
# 这两个列表刻意不同：营养数据覆盖率需要能量，pair complement 不把
# 能量和维生素/矿物质差异混成同一个业务概念。
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
# 基础分的六个子分数总权重必须为 1；反馈不是第七个归一化子分数，而是
# 在加权基础分之后以有界 adjustment 叠加，避免正负反馈改变权重体系。
BASE_SCORE_WEIGHTS = {
    "explicit_preference": 0.30,
    "taste_match": 0.25,
    "availability_and_season": 0.20,
    "price_match_score": 0.10,
    "convenience_score": 0.10,
    "history_diversity_score": 0.05,
}
# pair 分首先使用两种水果个人分的平均值，再加入互补、感官差异和组合新颖度。
# 这也是为什么不能先选第一名，再贪心选一个“第二名”替代完整组合枚举。
PAIR_SCORE_WEIGHTS = {
    "individual_mean": 0.70,
    "nutrition_pair": 0.15,
    "sensory_category_diversity": 0.10,
    "pair_novelty": 0.05,
}
# change_requested 记录换组事件，但不代表用户长期喜欢或不喜欢某种水果。
# 反馈权重和衰减窗口是启发式参数；修改它们会改变排序和理由，应单独测试。
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
# 衰减 tau 是算法语义，不等于 Application Service 查询最近多少天的数据。
FEEDBACK_DECAY_DAYS = {
    "liked": 120.0,
    "disliked": 180.0,
    "unavailable": 7.0,
    "expensive": 14.0,
    "tired_of_it": 10.0,
}
MIN_FEEDBACK_ADJUSTMENT = -0.15
MAX_FEEDBACK_ADJUSTMENT = 0.15
# 近优阈值只控制可复现随机选择的候选集合，不会把任意低分组合变成随机结果。
PAIR_NEAR_TOP_THRESHOLD = 0.03
EXPLORATION_COLD_START_PENALTY = 0.08
# history 的展示和吃过次数分别衰减；Repository 的日期窗口只决定传入哪些事件。
HISTORY_SHOWN_WEIGHT = 0.12
HISTORY_EATEN_WEIGHT = 0.18
HISTORY_SHOWN_TAU_DAYS = 7.0
HISTORY_EATEN_TAU_DAYS = 10.0
# 跨天水果冷却只看昨天；今天的换组由 excluded_pair 负责，不能重复计算。
FRUIT_COOLDOWN_DAYS = 1


class RecommendationError(Exception):
    """Base class for understandable recommendation domain errors."""


class InvalidRecommendationInputError(RecommendationError):
    """Raised when data passed to the pure algorithm is invalid."""


class NoRecommendationCandidatesError(RecommendationError):
    """Raised when fewer than two eligible fruits remain."""


def clamp_score(value: float) -> float:
    """将分数限制在 [0, 1]，同时拒绝 NaN/无穷值。"""

    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidRecommendationInputError("分数必须是有限数值")
    return min(1.0, max(0.0, numeric))


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


def _portion_value(value: float | None, portion_grams: float) -> float | None:
    """将一个营养字段按建议份量比例换算，保留缺失值。"""
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise InvalidRecommendationInputError("营养字段必须是非负有限数值")
    return numeric * portion_grams / 100.0


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

    ``default_portion_grams`` 会参与比例换算；演示 CSV 是无物理单位分数，
    所以该换算是当前已知的语义技术债，而非真实克/毫克计算。
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
    eligible: list[RecommendationFruit] = []
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
    """先过滤，再把每个候选映射为可解释的 ScoreBreakdown。

    营养归一化仍基于全部 active 水果；只有过滤后的水果进入单水果评分。
    算法需要至少两个候选，候选不足会抛出领域错误而不是返回重复水果。
    """

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
    return [
        float(value)
        for feature in features
        if (value := getattr(profile, feature, None)) is not None
    ]


def nutrition_complement_score(
    first: NutritionProfile,
    second: NutritionProfile,
) -> float:
    """计算两种水果的营养覆盖、多样性和缺失数据置信度。

    ``coverage`` 取每个特征两者的较高值，``diversity`` 取两者差异，
    ``confidence`` 按双方都已知的维度比例缩放。它只服务 pair complement，
    不等同于单水果的 nutrition richness；缺少共同特征时返回 0，而不是
    把缺失解释成营养不足或额外奖励。
    """
    pairs = [
        (getattr(first, feature, None), getattr(second, feature, None))
        for feature in NUTRITION_PAIR_FEATURES
    ]
    # 只有两种水果都具备的维度才有可比性；单边缺失不参与差异计算。
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
    """为已排除、近期出现或历史组合返回不同强度的新颖度。

    ``excluded_pair`` 是换一组的硬排除；``previous_pairs`` 只降分，历史
    水果事件则用于更细粒度地降低近期重复。优先使用带日期的
    ``history_events``，没有事件时才退回旧的 ``recent_fruit_ids``。
    """
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
    """用类别、食用方式和四个口感维度衡量组合差异。"""
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
    *,
    enforce_pair_cooldown: bool,
    blocked_recent_fruit_ids: frozenset[int],
) -> bool:
    """判断两个水果能否组成当前推荐组合。

    参数说明：
    - ``first`` / ``second``：准备组成组合的两个 ``RecommendationFruit``。
    - ``user``：当前用户的 ``RecommendationUser``，包含尝鲜等级和水果偏好。
    - ``context``：本次推荐的上下文，包括手动换组和短期组合冷却。
    - ``enforce_pair_cooldown``：是否启用最近几天的完整组合硬冷却。
    - ``blocked_recent_fruit_ids``：当前阶段要尽量避开的跨天水果 ID。

    返回值：
    - ``True``：该组合满足硬性规则，可以继续计算组合分数。
    - ``False``：该组合违反硬性规则，不能进入候选组合列表。

    ``filter_eligible_fruits`` 已经负责 inactive、forbidden、unavailable 等
    单水果硬过滤；本函数补充短期重复和需要同时观察两个水果的尝鲜组合规则。
    注意：``has_tried`` 有三种状态：
    - ``True``：用户明确吃过；
    - ``False``：用户明确没吃过；
    - ``None``：未知，不能当成没吃过或吃过。
    """

    # 用 frozenset 表示无序的水果组合：A+B 和 B+A 被视为同一组。
    pair = frozenset({first.id, second.id})

    # 换一组时，核心算法不能再次返回被排除的上一组组合。
    if context.excluded_pair is not None and pair == context.excluded_pair:
        return False

    # 正常阶段不允许最近几天已经出现过的完整组合；候选不足时由调用方
    # 关闭该开关，进入第三阶段放宽跨天组合冷却。
    if enforce_pair_cooldown and pair in context.cooldown_pairs:
        return False

    # 第一阶段尽量不让昨天出现过的单个水果连续出现；第二阶段传入空集合
    # 以便在候选不足时保留组合冷却、放宽单水果冷却。
    if first.id in blocked_recent_fruit_ids or second.id in blocked_recent_fruit_ids:
        return False

    # 读取用户保存的水果偏好；字典的键是 fruit_id。
    preferences = user.fruit_preferences

    # 只取当前这两个水果各自的偏好，列表中的元素可能是 None，表示用户没有填写偏好。
    pair_preferences = [preferences.get(first.id), preferences.get(second.id)]

    explicit_untried_count = sum(
        preference is not None and preference.has_tried is False
        for preference in pair_preferences
    )

    # has_tried 的语义：
    # True  = 用户明确吃过
    # False = 用户明确没吃过
    # None  = 用户尚未提供信息，不能当作“没吃过”
    #
    # 保守模式：组合中不能包含明确没吃过的水果。
    if user.discovery_level == 0 and explicit_untried_count > 0:
        return False

    # 均衡和尝鲜模式：一组最多包含一个明确没吃过的水果。
    # 不再强制组合必须包含 has_tried=True 的水果，
    # 避免少数已标记为吃过的水果成为每组必须出现的锚点。
    if user.discovery_level in {1, 2} and explicit_untried_count > 1:
        return False

    # 所有硬性规则均通过，组合可以进入后续评分。
    return True


def _recently_shown_fruit_ids(
    context: RecommendationContext,
    *,
    days: int,
) -> frozenset[int]:
    """提取跨天短窗口内出现过的水果，不把当天记录算入冷却。

    ``history_events`` 使用业务日期而不是写入时间；严格使用
    ``0 < difference <= days``，因此当天“换一组”由 ``excluded_pair`` 处理，
    不会和跨天冷却混在一起。没有事件时返回空集合，兼容旧的纯算法调用。
    """

    if days < 0:
        raise InvalidRecommendationInputError("冷却天数不能为负数")
    today = context.today or date.today()
    return frozenset(
        event.fruit_id
        for event in context.history_events
        if 0 < (today - event.occurred_on).days <= days
    )


def select_recommendation_pair(
    fruits: Iterable[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
) -> PairSelection:
    """枚举所有合法组合，按组合公式排序并稳定选择近优组合。

    对 ``n`` 个单水果候选枚举 ``n * (n - 1) / 2`` 个无序 pair，避免
    “先选冠军、再贪心选第二名”漏掉营养或感官互补更好的组合。组合硬过滤
    按“昨天水果 → 最近 3 天完整组合 → 跨天组合冷却”分层放宽，但
    ``excluded_pair`` 在任何阶段都不恢复。排序先按 pair_score 再按水果 ID
    稳定打破平分；提供 ``random_seed`` 时只在最高分上下
    ``PAIR_NEAR_TOP_THRESHOLD`` 的集合内选择。
    """

    fruit_list = list(fruits)
    scored = score_candidates(fruit_list, user, context)
    normalized = normalize_nutrition_profiles(
        [fruit for fruit in fruit_list if fruit.is_active]
    )
    recently_shown = _recently_shown_fruit_ids(
        context,
        days=FRUIT_COOLDOWN_DAYS,
    )

    def build_pairs(
        *,
        enforce_pair_cooldown: bool,
        blocked_recent_fruit_ids: frozenset[int],
    ) -> list[tuple[float, float, float, float, ScoredFruit, ScoredFruit]]:
        """在一个冷却阶段枚举全部组合；阶段只改变硬过滤，不改变评分。"""

        candidates: list[
            tuple[float, float, float, float, ScoredFruit, ScoredFruit]
        ] = []
        for first, second in combinations(scored, 2):
            if not _pair_is_legal(
                first.fruit,
                second.fruit,
                user,
                context,
                enforce_pair_cooldown=enforce_pair_cooldown,
                blocked_recent_fruit_ids=blocked_recent_fruit_ids,
            ):
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
            candidates.append(
                (pair_score, nutrition_pair, sensory, novelty, first, second)
            )
        return candidates

    # 第一阶段：最近 3 天完整组合不重复，并尽量避开昨天的单个水果。
    pairs = build_pairs(
        enforce_pair_cooldown=True,
        blocked_recent_fruit_ids=recently_shown,
    )
    # 第二阶段：候选不足时允许昨天的水果再次出现，但保留完整组合冷却。
    if not pairs:
        pairs = build_pairs(
            enforce_pair_cooldown=True,
            blocked_recent_fruit_ids=frozenset(),
        )
    # 第三阶段：限制仍过多时放开跨天组合冷却；excluded_pair 仍是硬约束。
    if not pairs:
        pairs = build_pairs(
            enforce_pair_cooldown=False,
            blocked_recent_fruit_ids=frozenset(),
        )
    if not pairs:
        raise NoRecommendationCandidatesError(
            "没有满足熟悉度和可推荐规则的水果组合，请调整尝鲜设置"
        )
    # 先固定顺序，再对近优集合做带 seed 的选择，保证同一上下文可复现。
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
    """生成恰好两个水果，并从相同评分贡献构造推荐理由。

    这里是纯算法对外的主入口：它只组合领域对象，不负责写库、事务或
    API 状态码。返回的 ``total_score`` 是 pair 分，单项 ``score`` 仍保留
    各水果的 base score，理由由同一批子分数计算，避免理由与排序脱节。
    """

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
    """按实际贡献排序理由，并限制返回条数。

    探索理由表达“尚未尝试”这一状态，不等于用户喜欢它；显式喜欢理由
    只有在熟悉水果且偏好分达到阈值时才出现。pair/nutrition 理由使用组合
    分贡献，强制把正反馈塞进前四项可能改变纯贡献排序，这是当前实现的
    解释取舍而非新的评分规则。
    """
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
        # 用绝对贡献排序可以同时展示正向匹配和负向修正，但 message/code
        # 仍必须与真实 component 对应，不能把缺失或未知写成偏好。
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
    """将单水果偏好映射为 0～1 的个人匹配先验。

    当前兼容逻辑对 ``has_tried=False`` 直接使用 commonness，不读取
    ``preference_score``；其它状态只要有 preference_score 就会读取，
    因而 UNKNOWN 行若同时带有偏好分也会影响排序。这是当前实现事实，
    与“偏好分只描述已吃过水果”的理想语义并不完全一致，本任务不改动它。
    """
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
    """Lower unfamiliar exploration fruits, unless the user explicitly likes one.

    这里的“explicitly liked”当前只检查 preference_score>=1，没有再次要求
    ``has_tried=True``；这与 FruitPreference 的理想字段语义存在边界差异，
    但保持现状是为了不在注释任务中改变排序。
    """
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
    fruit: RecommendationFruit,
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
    """验证可选的单位区间分数；``None`` 表示未提供，不代表 0。"""
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
