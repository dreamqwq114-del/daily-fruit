"""用户资料与水果偏好的 API 输入/输出合同。

Pydantic Schema 与 SQLAlchemy Model 分离：Schema 负责请求边界、默认值、
枚举范围和跨字段冲突；Service 再把经过验证的数据写入 ORM。未提供的
``UserUpdate`` 字段不会被提交，因此支持安全的部分更新。
"""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, field_validator, model_validator

from app.schemas.common import (
    ApiSchema,
    AwareDatetime,
    NormalizedScore,
    OptionalPreferenceScore,
    PositiveId,
    PreferenceScore,
)


Username = Annotated[str, Field(min_length=1, max_length=80)]
LocationName = Annotated[str, Field(min_length=1, max_length=100)]
PriceLevel = Annotated[int, Field(ge=1, le=3)]
DiscoveryLevel = Annotated[int, Field(ge=0, le=2)]
ConsumptionHorizonDays = Literal[2, 4, 7]
MarketAccessLevel = Annotated[StrictInt, Field(ge=1, le=3)]


class UserBase(ApiSchema):
    """创建和读取用户资料共用的业务字段。"""

    username: Username
    region: LocationName
    sweet_preference: NormalizedScore | None = None
    sour_preference: NormalizedScore | None = None
    soft_preference: NormalizedScore | None = None
    crisp_preference: NormalizedScore | None = None
    price_level: PriceLevel
    convenience_preference: NormalizedScore
    discovery_level: DiscoveryLevel = 1
    consumption_horizon_days: ConsumptionHorizonDays = 4
    market_access_level: MarketAccessLevel = 2
    accepts_online_purchase: StrictBool = False


class UserCreate(UserBase):
    # City is retained for backward compatibility with existing profiles, but
    # the current settings UI no longer collects it.
    city: LocationName = "UNKNOWN"


class UserUpdate(ApiSchema):
    """只包含调用方明确提交的字段，避免默认值覆盖已有资料。"""

    username: Username | None = None
    city: LocationName | None = None
    region: LocationName | None = None
    sweet_preference: NormalizedScore | None = None
    sour_preference: NormalizedScore | None = None
    soft_preference: NormalizedScore | None = None
    crisp_preference: NormalizedScore | None = None
    price_level: PriceLevel | None = None
    convenience_preference: NormalizedScore | None = None
    discovery_level: DiscoveryLevel | None = None
    consumption_horizon_days: ConsumptionHorizonDays | None = None
    market_access_level: MarketAccessLevel | None = None
    accepts_online_purchase: StrictBool | None = None

    @model_validator(mode="after")
    def require_non_null_update(self) -> "UserUpdate":
        """拒绝空 JSON 或显式 null，保持字段级更新语义清晰。"""

        if not self.model_fields_set:
            raise ValueError("At least one user field must be provided")
        if any(
            getattr(self, field_name) is None
            for field_name in self.model_fields_set
        ):
            raise ValueError("Updated user fields must not be null")
        return self


class UserRead(UserBase):
    id: PositiveId
    city: LocationName
    created_at: AwareDatetime
    updated_at: AwareDatetime


class UserFruitPreferenceInput(ApiSchema):
    """单个水果偏好的输入；熟悉度字段可选以兼容旧客户端。"""

    fruit_id: PositiveId
    preference_score: OptionalPreferenceScore = None
    is_forbidden: bool = False
    has_tried: bool | None = None
    willing_to_try: bool | None = None

    @model_validator(mode="after")
    def reject_untried_favorite(self) -> "UserFruitPreferenceInput":
        """阻止“特别喜欢且明确没吃过”或“喜欢且禁止”这类矛盾组合。"""

        if self.preference_score == 2 and self.has_tried is False:
            raise ValueError(
                "A fruit marked as especially loved cannot also be marked as not tried"
            )
        if self.preference_score == 2 and self.is_forbidden:
            raise ValueError(
                "A fruit cannot be both especially loved and forbidden"
            )
        return self


class UserFruitPreferencesUpdate(ApiSchema):
    """偏好批量合并请求；同一水果只能出现一次，特别喜欢最多五个。"""

    preferences: list[UserFruitPreferenceInput] = Field(default_factory=list)
    # Optional in the request for backward compatibility.  When supplied, the
    # list replaces the current type-level records in the same transaction;
    # ``preference=None`` means clear that option back to unknown.
    option_preferences: list["UserFruitOptionPreferenceInput"] = Field(
        default_factory=list
    )

    @field_validator("preferences")
    @classmethod
    def reject_duplicate_fruits(
        cls,
        preferences: list[UserFruitPreferenceInput],
    ) -> list[UserFruitPreferenceInput]:
        """在进入 service 前拒绝重复水果和超出上限的收藏。"""

        fruit_ids = [preference.fruit_id for preference in preferences]
        if len(fruit_ids) != len(set(fruit_ids)):
            raise ValueError("Each fruit may appear only once")
        favorite_count = sum(
            preference.preference_score == 2
            for preference in preferences
        )
        if favorite_count > 5:
            raise ValueError("At most five fruits may be marked as especially loved")
        return preferences

    @field_validator("option_preferences")
    @classmethod
    def reject_duplicate_options(
        cls,
        preferences: list["UserFruitOptionPreferenceInput"],
    ) -> list["UserFruitOptionPreferenceInput"]:
        keys = [(item.fruit_id, item.option_id) for item in preferences]
        if len(keys) != len(set(keys)):
            raise ValueError("Each fruit selection option may appear only once")
        return preferences


class UserFruitOptionPreferenceInput(ApiSchema):
    """消费类型偏好；省略记录或传 ``null`` 都表示 unknown/清除。"""

    fruit_id: PositiveId
    option_id: PositiveId
    preference: Literal["liked", "disliked"] | None = None


class UserFruitOptionPreferenceRead(UserFruitOptionPreferenceInput):
    id: PositiveId
    user_id: PositiveId
    preference: Literal["liked", "disliked"]
    created_at: AwareDatetime
    updated_at: AwareDatetime


class UserFruitPreferenceRead(UserFruitPreferenceInput):
    id: PositiveId
    user_id: PositiveId
    created_at: AwareDatetime
    updated_at: AwareDatetime


__all__ = [
    "UserCreate",
    "UserFruitPreferenceInput",
    "UserFruitPreferenceRead",
    "UserFruitOptionPreferenceInput",
    "UserFruitOptionPreferenceRead",
    "UserFruitPreferencesUpdate",
    "UserRead",
    "UserUpdate",
]
