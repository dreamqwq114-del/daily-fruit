"""基于真实评分贡献生成可解释推荐理由。"""

from __future__ import annotations

from app.schemas.recommendation import (
    ReasonCode,
    ReasonComponent,
    RecommendationReason,
)
from app.services.recommendation_types import (
    PairSelection,
    RecommendationUser,
    ScoredFruit,
)

from .common import clamp_score
from .fruit_evaluation import BASE_SCORE_WEIGHTS
from .pair_selection import PAIR_SCORE_WEIGHTS

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
