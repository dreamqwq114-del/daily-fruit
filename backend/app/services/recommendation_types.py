from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Mapping, Sequence

from app.schemas.recommendation import RecommendationReason


@dataclass(frozen=True, slots=True)
class NutritionProfile:
    energy: float | None = None
    vitamin_c: float | None = None
    fiber: float | None = None
    potassium: float | None = None
    folate: float | None = None
    carotenoids: float | None = None


@dataclass(frozen=True, slots=True)
class SeasonWindow:
    region: str
    start_month: int
    end_month: int
    season_score: float
    region_level: str = "national"
    availability_score: float = 0.45
    supply_status: str = "unknown"


@dataclass(frozen=True, slots=True)
class FruitPreference:
    preference_score: float | None = None
    is_forbidden: bool = False
    has_tried: bool | None = None
    willing_to_try: bool | None = None


@dataclass(frozen=True, slots=True)
class HistoryEvent:
    fruit_id: int
    occurred_on: date
    times_shown: int = 1
    eaten_count: int = 0


@dataclass(frozen=True, slots=True)
class FeedbackEvent:
    fruit_id: int
    feedback_type: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class RecommendationFruit:
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
    score: float
    has_relevant_data: bool
    is_in_season: bool
    availability_score: float = 0.45
    supply_status: str = "unknown"
    region_rank: int = 0


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
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
    fruit: RecommendationFruit
    base_score: float
    scores: ScoreBreakdown
    season: SeasonEvaluation


@dataclass(frozen=True, slots=True)
class PairSelection:
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
