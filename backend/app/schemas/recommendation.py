from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator

from app.schemas.common import (
    ApiSchema,
    AwareDatetime,
    PositiveId,
    RecommendationScore,
    RefreshNumber,
)
from app.schemas.fruit import FruitDetail


class RecommendationStatus(StrEnum):
    ACTIVE = "active"
    REPLACED = "replaced"


class FeedbackType(StrEnum):
    EATEN = "eaten"
    LIKED = "liked"
    DISLIKED = "disliked"
    UNAVAILABLE = "unavailable"
    EXPENSIVE = "expensive"
    TIRED_OF_IT = "tired_of_it"
    CHANGE_REQUESTED = "change_requested"


class ReasonCode(StrEnum):
    IN_SEASON = "in_season"
    SWEET_MATCH = "sweet_match"
    SOUR_MATCH = "sour_match"
    SOFT_MATCH = "soft_match"
    CRISP_MATCH = "crisp_match"
    PRICE_MATCH = "price_match"
    NOT_RECENTLY_RECOMMENDED = "not_recently_recommended"
    CONVENIENT = "convenient"
    NUTRITION_DIVERSITY = "nutrition_diversity"
    NUTRITION_COMPLEMENT = "nutrition_complement"
    FEEDBACK_MATCH = "feedback_match"
    EXPLICIT_PREFERENCE = "explicit_preference"
    EXPLORATION = "exploration"
    AVAILABILITY = "availability"
    HISTORY_FRESHNESS = "history_freshness"
    PAIR_NOVELTY = "pair_novelty"
    DEFAULT_MATCH = "default_match"


class ReasonComponent(StrEnum):
    SEASON_SCORE = "season_score"
    PREFERENCE_SCORE = "preference_score"
    NUTRITION_DIVERSITY_SCORE = "nutrition_diversity_score"
    HISTORY_DIVERSITY_SCORE = "history_diversity_score"
    CONVENIENCE_SCORE = "convenience_score"
    PRICE_MATCH_SCORE = "price_match_score"
    COMPLEMENT_SCORE = "complement_score"
    FEEDBACK_ADJUSTMENT = "feedback_adjustment"
    EXPLICIT_PREFERENCE = "explicit_preference"
    TASTE_MATCH = "taste_match"
    AVAILABILITY_SCORE = "availability_score"
    HISTORY_FRESHNESS = "history_freshness"
    PAIR_SCORE = "pair_score"
    PAIR_NOVELTY = "pair_novelty"
    FAMILIARITY = "familiarity"


class RecommendationReason(ApiSchema):
    code: ReasonCode
    message: Annotated[str, Field(min_length=1, max_length=200)]
    component: ReasonComponent
    contribution: RecommendationScore = 0


Reasons = Annotated[
    list[RecommendationReason],
    Field(min_length=2, max_length=4),
]
Rank = Annotated[int, Field(ge=1, le=2)]


class RecommendationItemCreate(ApiSchema):
    fruit_id: PositiveId
    score: RecommendationScore
    rank: Rank
    reasons: Reasons
    individual_score: RecommendationScore | None = None
    pair_score: RecommendationScore | None = None
    nutrition_pair_score: RecommendationScore | None = None


class RecommendationItemRead(RecommendationItemCreate):
    id: PositiveId
    recommendation_id: PositiveId
    created_at: AwareDatetime


class RecommendationBase(ApiSchema):
    user_id: PositiveId
    recommendation_date: date
    refresh_number: RefreshNumber
    total_score: RecommendationScore
    status: RecommendationStatus = RecommendationStatus.ACTIVE


def _validate_recommendation_pair(
    items: list[RecommendationItemCreate | RecommendationItemRead],
) -> list[RecommendationItemCreate | RecommendationItemRead]:
    if {item.rank for item in items} != {1, 2}:
        raise ValueError("Recommendation items must have ranks 1 and 2")
    if len({item.fruit_id for item in items}) != 2:
        raise ValueError("Recommendation items must use distinct fruits")
    return items


class RecommendationCreate(RecommendationBase):
    items: Annotated[
        list[RecommendationItemCreate],
        Field(min_length=2, max_length=2),
    ]

    @field_validator("items")
    @classmethod
    def validate_item_pair(
        cls,
        items: list[RecommendationItemCreate],
    ) -> list[RecommendationItemCreate]:
        return list(_validate_recommendation_pair(items))


class RecommendationRead(RecommendationBase):
    id: PositiveId
    created_at: AwareDatetime
    items: Annotated[
        list[RecommendationItemRead],
        Field(min_length=2, max_length=2),
    ]

    @field_validator("items")
    @classmethod
    def validate_item_pair(
        cls,
        items: list[RecommendationItemRead],
    ) -> list[RecommendationItemRead]:
        return list(_validate_recommendation_pair(items))


class RecommendationRefreshRequest(ApiSchema):
    user_id: PositiveId


class RecommendationFeedbackCreate(ApiSchema):
    feedback_type: FeedbackType
    comment: Annotated[str, Field(max_length=1000)] | None = None


class RecommendationFeedbackRead(RecommendationFeedbackCreate):
    id: PositiveId
    recommendation_item_id: PositiveId
    user_id: PositiveId
    created_at: AwareDatetime


class RecommendationItemDetail(RecommendationItemRead):
    fruit: FruitDetail
    feedback: list[RecommendationFeedbackRead] = Field(default_factory=list)


class RecommendationDetail(RecommendationBase):
    id: PositiveId
    created_at: AwareDatetime
    items: Annotated[
        list[RecommendationItemDetail],
        Field(min_length=2, max_length=2),
    ]

    @field_validator("items")
    @classmethod
    def validate_item_pair(
        cls,
        items: list[RecommendationItemDetail],
    ) -> list[RecommendationItemDetail]:
        return list(_validate_recommendation_pair(items))


__all__ = [
    "FeedbackType",
    "ReasonCode",
    "ReasonComponent",
    "RecommendationCreate",
    "RecommendationDetail",
    "RecommendationFeedbackCreate",
    "RecommendationFeedbackRead",
    "RecommendationItemCreate",
    "RecommendationItemDetail",
    "RecommendationItemRead",
    "RecommendationRead",
    "RecommendationReason",
    "RecommendationRefreshRequest",
    "RecommendationStatus",
]
