from typing import Annotated

from pydantic import Field

from app.schemas.common import (
    ApiSchema,
    AwareDatetime,
    Month,
    NormalizedScore,
    NutritionValue,
    PositiveId,
)


FruitName = Annotated[str, Field(min_length=1, max_length=100)]
Category = Annotated[str, Field(min_length=1, max_length=80)]
TasteLabel = Annotated[str, Field(min_length=1, max_length=120)]
DefaultPortion = Annotated[str, Field(min_length=1, max_length=80)]
RegionName = Annotated[str, Field(min_length=1, max_length=100)]
PriceLevel = Annotated[int, Field(ge=1, le=3)]


class FruitBase(ApiSchema):
    name: FruitName
    category: Category
    taste: TasteLabel
    sweet_score: NormalizedScore
    sour_score: NormalizedScore
    soft_score: NormalizedScore
    crisp_score: NormalizedScore
    convenience_score: NormalizedScore
    average_price_level: PriceLevel
    default_portion: DefaultPortion
    image_url: Annotated[str, Field(max_length=2048)] | None = None
    description: Annotated[str, Field(min_length=1)]
    is_active: bool = True


class FruitRead(FruitBase):
    id: PositiveId
    created_at: AwareDatetime
    updated_at: AwareDatetime


class FruitNutritionBase(ApiSchema):
    energy: NutritionValue
    vitamin_c: NutritionValue
    fiber: NutritionValue
    potassium: NutritionValue
    folate: NutritionValue
    carotenoids: NutritionValue


class FruitNutritionRead(FruitNutritionBase):
    id: PositiveId
    fruit_id: PositiveId
    created_at: AwareDatetime
    updated_at: AwareDatetime


class FruitSeasonBase(ApiSchema):
    region: RegionName
    start_month: Month
    end_month: Month
    season_score: NormalizedScore


class FruitSeasonRead(FruitSeasonBase):
    id: PositiveId
    fruit_id: PositiveId
    created_at: AwareDatetime


class FruitDetail(FruitRead):
    nutrition: FruitNutritionRead | None = None
    seasons: list[FruitSeasonRead] = Field(default_factory=list)


__all__ = [
    "FruitBase",
    "FruitDetail",
    "FruitNutritionBase",
    "FruitNutritionRead",
    "FruitRead",
    "FruitSeasonBase",
    "FruitSeasonRead",
]
