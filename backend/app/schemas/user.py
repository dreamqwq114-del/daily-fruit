from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from app.schemas.common import (
    ApiSchema,
    AwareDatetime,
    NormalizedScore,
    PositiveId,
    PreferenceScore,
)


Username = Annotated[str, Field(min_length=1, max_length=80)]
LocationName = Annotated[str, Field(min_length=1, max_length=100)]
PriceLevel = Annotated[int, Field(ge=1, le=3)]


class UserBase(ApiSchema):
    username: Username
    city: LocationName
    region: LocationName
    sweet_preference: NormalizedScore
    sour_preference: NormalizedScore
    soft_preference: NormalizedScore
    crisp_preference: NormalizedScore
    price_level: PriceLevel
    convenience_preference: NormalizedScore


class UserCreate(UserBase):
    pass


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
    created_at: AwareDatetime
    updated_at: AwareDatetime


class UserFruitPreferenceInput(ApiSchema):
    fruit_id: PositiveId
    preference_score: PreferenceScore = Decimal("0")
    is_forbidden: bool = False


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
