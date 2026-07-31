from typing import Annotated

from pydantic import Field

from app.schemas.common import (
    ApiSchema,
    AwareDatetime,
    Month,
    NormalizedScore,
    NutritionValue,
    PortionGrams,
    PositiveId,
)


FruitName = Annotated[str, Field(min_length=1, max_length=100)]
Category = Annotated[str, Field(min_length=1, max_length=80)]
TasteLabel = Annotated[str, Field(min_length=1, max_length=120)]
DefaultPortion = Annotated[str, Field(min_length=1, max_length=80)]
RegionName = Annotated[str, Field(min_length=1, max_length=100)]
PriceLevel = Annotated[int, Field(ge=1, le=3)]
ConsumptionMode = Annotated[str, Field(pattern="^(direct|peel|cut|ingredient)$")]
DailyRecommendationRole = Annotated[
    str,
    Field(pattern="^(main|exploration|supporting)$"),
]
DataQuality = Annotated[str, Field(pattern="^(high|medium|low)$")]
RegionLevel = Annotated[str, Field(pattern="^(city|province|area|national)$")]
SupplyStatus = Annotated[
    str,
    Field(pattern="^(available|unknown|unavailable)$"),
]


class FruitBase(ApiSchema):
    code: Annotated[str, Field(min_length=1, max_length=60)] = "legacy"
    name: FruitName
    aliases: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list,
    )
    category: Category
    taste: TasteLabel
    sweet_score: NormalizedScore
    sour_score: NormalizedScore
    soft_score: NormalizedScore
    crisp_score: NormalizedScore
    convenience_score: NormalizedScore
    average_price_level: PriceLevel
    default_portion: DefaultPortion
    default_portion_grams: PortionGrams = 100
    direct_eating: bool = True
    consumption_mode: ConsumptionMode = "direct"
    daily_recommendation_role: DailyRecommendationRole = "main"
    preparation_difficulty: NormalizedScore = 0.5
    portability_score: NormalizedScore = 0.5
    messiness_score: NormalizedScore = 0.5
    storage_difficulty: NormalizedScore = 0.5
    aroma_intensity: NormalizedScore = 0.5
    commonness_score: NormalizedScore = 0.5
    novelty_level: Annotated[int, Field(ge=0, le=2)] = 1
    data_quality: DataQuality = "low"
    data_source_note: Annotated[str, Field(max_length=500)] | None = None
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
    region_level: RegionLevel = "national"
    start_month: Month
    end_month: Month
    season_score: NormalizedScore
    availability_score: NormalizedScore = 0.45
    supply_status: SupplyStatus = "unknown"


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
