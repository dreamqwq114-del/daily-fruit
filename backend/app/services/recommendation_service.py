"""纯推荐算法的稳定公开门面。

外部业务代码继续从本模块导入推荐 API；具体算法实现位于
recommendation_core 内部模块。门面只负责显式重导出和结果组装，
不访问数据库、网络或 FastAPI。
"""

from __future__ import annotations

from app.services.recommendation_core.common import (
    InvalidRecommendationInputError,
    NoRecommendationCandidatesError,
    RecommendationError,
    _validate_unit_scores,
    clamp_score,
)
from app.services.recommendation_core.fruit_evaluation import (
    BASE_SCORE_WEIGHTS,
    EXPLORATION_COLD_START_PENALTY,
    FEEDBACK_ADJUSTMENTS,
    FEEDBACK_DECAY_DAYS,
    HISTORY_EATEN_TAU_DAYS,
    HISTORY_EATEN_WEIGHT,
    HISTORY_SHOWN_TAU_DAYS,
    HISTORY_SHOWN_WEIGHT,
    MISSING_SEASON_SCORE,
    NUTRITION_FEATURES,
    NUTRITION_PAIR_FEATURES,
    MAX_FEEDBACK_ADJUSTMENT,
    MIN_FEEDBACK_ADJUSTMENT,
    _derived_convenience,
    _explicit_preference_score,
    _exploration_adjustment,
    _feedback_adjustment,
    _feedback_events_for,
    _history_freshness,
    _nutrition_index_value,
    _nutrition_values,
    _quantile,
    _score_fruit,
    _taste_match,
    _validate_inputs,
    calculate_base_score,
    evaluate_season,
    filter_eligible_fruits,
    month_is_in_range,
    normalize_nutrition_profiles,
    score_candidates,
)
from app.services.recommendation_core.pair_selection import (
    FRUIT_COOLDOWN_DAYS,
    PAIR_NEAR_TOP_THRESHOLD,
    PAIR_SCORE_WEIGHTS,
    _pair_is_legal,
    _pair_novelty,
    _recently_shown_fruit_ids,
    _sensory_category_diversity,
    nutrition_complement_score,
    select_recommendation_pair,
)
from app.services.recommendation_core.reasons import _build_reasons
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
