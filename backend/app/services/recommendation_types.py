"""推荐核心使用的纯 Python 数据合同。

这些 frozen/slots dataclass 是 ORM 与算法之间的边界：它们不携带 Session，
便于用固定输入测试季节、过滤、评分、组合和理由生成。新增字段前应先
确认 mapper、算法和测试是否都需要它。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Mapping, Sequence

from app.schemas.recommendation import RecommendationReason


@dataclass(frozen=True, slots=True)
class NutritionProfile:
    """水果营养特征；None 表示缺失而不是零。"""

    energy: float | None = None
    vitamin_c: float | None = None
    fiber: float | None = None
    potassium: float | None = None
    folate: float | None = None
    carotenoids: float | None = None


@dataclass(frozen=True, slots=True)
class SeasonWindow:
    """一条地区和月份季节/供应窗口，支持跨年月份。"""

    region: str
    start_month: int
    end_month: int
    season_score: float
    region_level: str = "national"
    availability_score: float = 0.45
    supply_status: str = "unknown"


@dataclass(frozen=True, slots=True)
class FruitPreference:
    """用户对单个水果的显式态度、禁止和熟悉度信号。"""

    preference_score: float | None = None
    is_forbidden: bool = False
    has_tried: bool | None = None
    willing_to_try: bool | None = None


@dataclass(frozen=True, slots=True)
class HistoryEvent:
    """历史展示/食用聚合事件，用于时间衰减去重。"""

    fruit_id: int
    occurred_on: date
    times_shown: int = 1
    eaten_count: int = 0


@dataclass(frozen=True, slots=True)
class FeedbackEvent:
    """带时间的用户反馈，用于反馈调整衰减。"""

    fruit_id: int
    feedback_type: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class RecommendationFruit:
    """算法需要的水果快照，脱离 SQLAlchemy ORM 后仍可独立评分。"""

    id: int
    name: str
    sweet_score: float
    sour_score: float
    soft_score: float
    crisp_score: float
    convenience_score: float
    average_price_level: int
    category: str = ""
    taste: str = ""
    code: str = ""
    aliases: tuple[str, ...] = ()
    default_portion_grams: float = 100.0
    direct_eating: bool = True
    consumption_mode: str = "direct"
    daily_recommendation_role: str = "main"
    preparation_difficulty: float = 0.5
    portability_score: float = 0.5
    messiness_score: float = 0.5
    storage_difficulty: float = 0.5
    aroma_intensity: float = 0.5
    commonness_score: float = 0.5
    novelty_level: int = 1
    data_quality: str = "low"
    data_source_note: str | None = None
    is_active: bool = True
    nutrition: NutritionProfile | None = None
    seasons: tuple[SeasonWindow, ...] = ()


@dataclass(frozen=True, slots=True)
class RecommendationUser:
    """算法需要的用户画像；不包含 auth UUID 或数据库主键。"""

    region: str
    sweet_preference: float | None
    sour_preference: float | None
    soft_preference: float | None
    crisp_preference: float | None
    price_level: int
    convenience_preference: float
    city: str = ""
    discovery_level: int = 1
    fruit_preferences: Mapping[int, FruitPreference] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class RecommendationContext:
    """一次推荐计算的日期、历史、反馈、刷新排除和随机种子。"""

    month: int
    today: date | None = None
    recent_fruit_ids: tuple[int, ...] = ()
    feedback_by_fruit: Mapping[int, Sequence[str]] = field(
        default_factory=dict
    )
    random_seed: int | None = None
    exclude_disliked: bool = True
    history_events: tuple[HistoryEvent, ...] = ()
    feedback_events: tuple[FeedbackEvent, ...] = ()
    previous_pairs: tuple[frozenset[int], ...] = ()
    excluded_pair: frozenset[int] | None = None
    allow_supporting: bool = False


@dataclass(frozen=True, slots=True)
class SeasonEvaluation:
    """季节匹配结果，包含可用性与供应状态。"""

    score: float
    has_relevant_data: bool
    is_in_season: bool
    availability_score: float = 0.45
    supply_status: str = "unknown"
    region_rank: int = 0


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """单水果评分的可解释子分数，供公式和理由生成共同使用。"""

    explicit_preference: float
    taste_match: float
    availability_and_season: float
    price_match_score: float
    convenience_score: float
    history_diversity_score: float
    feedback_adjustment: float = 0.0
    season_score: float = 0.0
    availability_score: float = 0.45
    nutrition_diversity_score: float = 0.0
    familiarity_score: float = 0.5
    known_nutrition_ratio: float = 0.0
    preference_score: float = 0.0


@dataclass(frozen=True, slots=True)
class ScoredFruit:
    """水果及其单项分数和季节评估。"""

    fruit: RecommendationFruit
    base_score: float
    scores: ScoreBreakdown
    season: SeasonEvaluation


@dataclass(frozen=True, slots=True)
class PairSelection:
    """完整组合枚举后选出的两种水果及互补分。"""

    first: ScoredFruit
    second: ScoredFruit
    second_score: float
    complement_score: float
    pair_score: float = 0.0
    nutrition_pair_score: float = 0.0
    sensory_category_diversity: float = 0.0
    pair_novelty: float = 1.0


@dataclass(frozen=True, slots=True)
class RecommendationItemResult:
    """可持久化/返回 API 的单项推荐结果。"""

    fruit: RecommendationFruit
    score: float
    rank: int
    reasons: tuple[RecommendationReason, ...]
    base_score: float
    complement_score: float | None = None
    individual_score: float | None = None
    pair_score: float | None = None
    nutrition_pair_score: float | None = None


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    """一次推荐必须恰好包含两个不同 rank 的水果。"""

    items: tuple[RecommendationItemResult, RecommendationItemResult]
    total_score: float


__all__ = [
    "FruitPreference",
    "FeedbackEvent",
    "HistoryEvent",
    "NutritionProfile",
    "PairSelection",
    "RecommendationContext",
    "RecommendationFruit",
    "RecommendationItemResult",
    "RecommendationResult",
    "RecommendationUser",
    "ScoredFruit",
    "ScoreBreakdown",
    "SeasonEvaluation",
    "SeasonWindow",
]
