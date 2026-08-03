"""两种水果的营养互补、合法性和组合选择。

本模块枚举完整水果对并执行组合级硬约束。跨天冷却按既定顺序逐级放宽，
但 ``excluded_pair`` 始终是不可放宽的换组约束；最终只返回算法核心选定
的 ``PairSelection``，不负责持久化或 HTTP 编排。
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from datetime import date
from itertools import combinations
from typing import cast

from app.services.recommendation_types import (
    NutritionProfile,
    PairSelection,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    ScoredFruit,
)

from .common import (
    InvalidRecommendationInputError,
    NoRecommendationCandidatesError,
    clamp_score,
)
from .fruit_evaluation import (
    NUTRITION_PAIR_FEATURES,
    _score_candidates_with_normalized,
)

PAIR_SCORE_WEIGHTS = {
    "individual_mean": 0.70,
    "nutrition_pair": 0.15,
    "sensory_category_diversity": 0.10,
    "pair_novelty": 0.05,
}
PAIR_NEAR_TOP_THRESHOLD = 0.03
FRUIT_COOLDOWN_DAYS = 1

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
    pairs: list[tuple[float | None, float | None]] = [
        (
            cast(float | None, getattr(first, feature, None)),
            cast(float | None, getattr(second, feature, None)),
        )
        for feature in NUTRITION_PAIR_FEATURES
    ]
    # 只有两种水果都具备的维度才有可比性；单边缺失不参与差异计算。
    known = [
        (float(cast(float, left)), float(cast(float, right)))
        for left, right in pairs
        if left is not None and right is not None
    ]
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
    first_resolved=None,
    second_resolved=None,
) -> float:
    """用四个真实口感维度衡量组合的体验差异。

    ``sensory_category_diversity`` 是稳定的 API 字段名；内部不再读取
    ``category``/``display_group``，避免展示分组改变推荐结果。
    """
    first_values = (
        first_resolved.effective_sweet_score,
        first_resolved.effective_sour_score,
        first_resolved.effective_soft_score,
        first_resolved.effective_crisp_score,
    ) if first_resolved is not None else (
        first.sweet_score,
        first.sour_score,
        first.soft_score,
        first.crisp_score,
    )
    second_values = (
        second_resolved.effective_sweet_score,
        second_resolved.effective_sour_score,
        second_resolved.effective_soft_score,
        second_resolved.effective_crisp_score,
    ) if second_resolved is not None else (
        second.sweet_score,
        second.sour_score,
        second.soft_score,
        second.crisp_score,
    )
    taste_distance = sum(
        abs(left - right)
        for left, right in zip(first_values, second_values)
    ) / 4
    return clamp_score(taste_distance)


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
    if user.discovery_level == 1 and explicit_untried_count > 1:
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
    scored, normalized = _score_candidates_with_normalized(
        fruit_list,
        user,
        context,
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
            sensory = _sensory_category_diversity(
                first.fruit,
                second.fruit,
                first.resolved_candidate,
                second.resolved_candidate,
            )
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
