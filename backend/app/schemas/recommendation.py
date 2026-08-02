"""推荐 API 的枚举、评分、理由、反馈和 pair 结构合同。"""

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
from app.schemas.fruit import FruitDetail, FruitFactRead


class RecommendationStatus(StrEnum):
    """推荐生命周期；active 是当天可见组，replaced 是历史旧组。"""

    ACTIVE = "active"
    REPLACED = "replaced"


class FeedbackType(StrEnum):
    """前端可提交的反馈事件类型。"""

    EATEN = "eaten"
    LIKED = "liked"
    DISLIKED = "disliked"
    UNAVAILABLE = "unavailable"
    EXPENSIVE = "expensive"
    TIRED_OF_IT = "tired_of_it"
    CHANGE_REQUESTED = "change_requested"


class ReasonCode(StrEnum):
    """推荐理由的稳定代码，便于前端展示和回归测试。"""

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
    """理由对应的评分贡献组件。"""

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
    """结构化理由：代码、文案、评分组件和归一化贡献。"""

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
    """保证每组推荐恰好有 rank 1/2 且水果不重复。"""

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
        """在创建请求边界再次验证两项组合。"""

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
        """验证从数据库读出的推荐仍满足两项合同。"""

        return list(_validate_recommendation_pair(items))


class RecommendationRefreshRequest(ApiSchema):
    user_id: PositiveId


class RecommendationFeedbackCreate(ApiSchema):
    """用户反馈请求；comment 可选且限制长度。"""

    feedback_type: FeedbackType
    comment: Annotated[str, Field(max_length=1000)] | None = None


class RecommendationFeedbackRead(RecommendationFeedbackCreate):
    id: PositiveId
    recommendation_item_id: PositiveId
    user_id: PositiveId
    created_at: AwareDatetime


class RecommendationItemDetail(RecommendationItemRead):
    fruit: FruitDetail
    daily_fact: FruitFactRead | None = None
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
        """验证带水果详情的最终 API 响应仍是两个不同水果。"""

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
