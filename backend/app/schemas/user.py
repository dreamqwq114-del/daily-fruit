from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

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


class UserBase(ApiSchema):
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


class UserCreate(UserBase):
    # City is retained for backward compatibility with existing profiles, but
    # the current settings UI no longer collects it.
    city: LocationName = "UNKNOWN"


class UserUpdate(ApiSchema):
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

    @model_validator(mode="after")
    def require_non_null_update(self) -> "UserUpdate":
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
    fruit_id: PositiveId
    preference_score: OptionalPreferenceScore = None
    is_forbidden: bool = False
    has_tried: bool | None = None
    willing_to_try: bool | None = None

    @model_validator(mode="after")
    def reject_untried_favorite(self) -> "UserFruitPreferenceInput":
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
    preferences: list[UserFruitPreferenceInput] = Field(default_factory=list)

    @field_validator("preferences")
    @classmethod
    def reject_duplicate_fruits(
        cls,
        preferences: list[UserFruitPreferenceInput],
    ) -> list[UserFruitPreferenceInput]:
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


class UserFruitPreferenceRead(UserFruitPreferenceInput):
    id: PositiveId
    user_id: PositiveId
    created_at: AwareDatetime
    updated_at: AwareDatetime


__all__ = [
    "UserCreate",
    "UserFruitPreferenceInput",
    "UserFruitPreferenceRead",
    "UserFruitPreferencesUpdate",
    "UserRead",
    "UserUpdate",
]
