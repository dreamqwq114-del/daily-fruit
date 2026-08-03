"""API contracts for product-level suggestions and issue reports."""

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from app.schemas.common import ApiSchema, AwareDatetime, PositiveId


ProductFeedbackContent = Annotated[
    str,
    Field(min_length=1, max_length=1000),
]


class ProductFeedbackCategory(StrEnum):
    """Stable categories accepted by the product-feedback endpoint."""

    RECOMMENDATION_QUALITY = "recommendation_quality"
    SUGGESTION = "suggestion"
    BUG = "bug"
    FRUIT_CONTENT = "fruit_content"
    OTHER = "other"


class ProductFeedbackPageKey(StrEnum):
    """Safe route names; raw URLs are deliberately never persisted."""

    TODAY = "today"
    PREFERENCES = "preferences"
    HISTORY = "history"


class ProductFeedbackStatus(StrEnum):
    """Lifecycle values maintained by the project operator."""

    NEW = "new"
    RESOLVED = "resolved"


class ProductFeedbackCreate(ApiSchema):
    """Client input; ownership and lifecycle fields are server controlled."""

    category: ProductFeedbackCategory
    content: ProductFeedbackContent
    page_key: ProductFeedbackPageKey | None = None


class ProductFeedbackRead(ApiSchema):
    """Safe response contract that omits business and Auth user identifiers."""

    id: PositiveId
    category: ProductFeedbackCategory
    content: ProductFeedbackContent
    page_key: ProductFeedbackPageKey | None = None
    status: ProductFeedbackStatus
    created_at: AwareDatetime


__all__ = [
    "ProductFeedbackCategory",
    "ProductFeedbackContent",
    "ProductFeedbackCreate",
    "ProductFeedbackPageKey",
    "ProductFeedbackRead",
    "ProductFeedbackStatus",
]
