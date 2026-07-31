from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from app.schemas.recommendation import RecommendationReason


@dataclass(frozen=True, slots=True)
class NutritionProfile:
    energy: float
    vitamin_c: float
    fiber: float
    potassium: float
    folate: float
    carotenoids: float


@dataclass(frozen=True, slots=True)
class SeasonWindow:
    region: str
    start_month: int
    end_month: int
    season_score: float


@dataclass(frozen=True, slots=True)
class FruitPreference:
    preference_score: float = 0.0
    is_forbidden: bool = False


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
    is_active: bool = True
    nutrition: NutritionProfile | None = None
    seasons: tuple[SeasonWindow, ...] = ()


@dataclass(frozen=True, slots=True)
class RecommendationUser:
    region: str
    sweet_preference: float
    sour_preference: float
    soft_preference: float
    crisp_preference: float
    price_level: int
    convenience_preference: float
    fruit_preferences: Mapping[int, FruitPreference] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class RecommendationContext:
    month: int
    recent_fruit_ids: tuple[int, ...] = ()
    feedback_by_fruit: Mapping[int, Sequence[str]] = field(
        default_factory=dict
    )
    random_seed: int | None = None
    exclude_disliked: bool = True


@dataclass(frozen=True, slots=True)
class SeasonEvaluation:
    score: float
    has_relevant_data: bool
    is_in_season: bool


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    season_score: float
    preference_score: float
    nutrition_diversity_score: float
    history_diversity_score: float
    convenience_score: float
    price_match_score: float
    feedback_adjustment: float = 0.0


@dataclass(frozen=True, slots=True)
class ScoredFruit:
    fruit: RecommendationFruit
    base_score: float
    scores: ScoreBreakdown
    season: SeasonEvaluation


@dataclass(frozen=True, slots=True)
class RecommendationItemResult:
    fruit: RecommendationFruit
    score: float
    rank: int
    reasons: tuple[RecommendationReason, ...]
    base_score: float
    complement_score: float | None = None


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    items: tuple[RecommendationItemResult, RecommendationItemResult]
    total_score: float


__all__ = [
    "FruitPreference",
    "NutritionProfile",
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
