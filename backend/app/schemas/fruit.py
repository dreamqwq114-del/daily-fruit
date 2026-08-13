from typing import Annotated, Literal

from pydantic import Field

from app.selection_option_policy import (
    SelectionMatchingMode,
    SelectionOptionScoreEffect,
    selection_matching_mode_for_code,
    selection_option_score_effect_for_code,
)

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
DisplayGroup = Annotated[str, Field(min_length=1, max_length=80)]
TasteLabel = Annotated[str, Field(min_length=1, max_length=120)]
DefaultPortion = Annotated[str, Field(min_length=1, max_length=80)]
RegionName = Annotated[str, Field(min_length=1, max_length=100)]
PriceLevel = Annotated[int, Field(ge=1, le=3)]
ConsumptionMode = Annotated[str, Field(pattern="^(direct|peel|cut|ingredient)$")]
DailyRecommendationRole = Annotated[
    str,
    Field(pattern="^(main|supporting)$"),
]
DataQuality = Annotated[str, Field(pattern="^(high|medium|low)$")]
FactType = Annotated[str, Field(pattern="^[a-z][a-z0-9_]{1,39}$")]
RegionLevel = Annotated[str, Field(pattern="^(city|province|area|national)$")]
SupplyStatus = Annotated[
    str,
    Field(pattern="^(available|unknown|unavailable)$"),
]
SeasonDataScope = Literal["harvest", "market", "legacy"]
SeasonDataQuality = Annotated[
    str,
    Field(pattern="^(high|medium|low|unverified)$"),
]
CultivationType = Literal["open_field", "protected", "mixed", "unknown"]
TypicalPurchaseStage = Literal["ready_to_eat", "needs_ripening", "variable"]


class FruitBase(ApiSchema):
    code: Annotated[str, Field(min_length=1, max_length=60)] = "legacy"
    name: FruitName
    aliases: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list,
    )
    category: Category
    display_group: Annotated[str, Field(max_length=80)] = ""
    taste: TasteLabel
    sweet_score: NormalizedScore
    sour_score: NormalizedScore
    soft_score: NormalizedScore
    crisp_score: NormalizedScore
    # Deprecated soft/crisp fields remain accepted for old clients; the new
    # algorithm reads texture_score when it is present.
    texture_score: NormalizedScore | None = None
    convenience_score: NormalizedScore
    ripe_storage_score: NormalizedScore | None = None
    typical_purchase_stage: TypicalPurchaseStage | None = None
    ripening_note: Annotated[str, Field(max_length=500)] | None = None
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
    # 默认值仅用于读取 0013 及更早的历史快照；字段缺失时按 code
    # 推导，已冻结的新快照保持原值。浏览器不再检查覆盖字段猜模式。
    selection_matching_mode: SelectionMatchingMode = "explicit-only"
    selection_option_score_effect: SelectionOptionScoreEffect = "profile-override"
    selection_options: list["FruitSelectionOptionRead"] = Field(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        # 0013 及更早的历史快照没有这两个字段；仅对缺失字段回退推导。
        # 已保存的新快照必须保留当时值，不能随当前策略变化。
        if "selection_matching_mode" not in self.model_fields_set:
            self.selection_matching_mode = selection_matching_mode_for_code(self.code)
        if "selection_option_score_effect" not in self.model_fields_set:
            self.selection_option_score_effect = (
                selection_option_score_effect_for_code(self.code)
            )


class FruitSelectionOptionRead(ApiSchema):
    """父水果下的可选消费类型，仅包含展示和口感覆盖字段。"""

    id: PositiveId
    fruit_id: PositiveId
    code: Annotated[str, Field(min_length=1, max_length=40)]
    name: Annotated[str, Field(min_length=1, max_length=100)]
    sweet_score: NormalizedScore | None = None
    sour_score: NormalizedScore | None = None
    soft_score: NormalizedScore | None = None
    crisp_score: NormalizedScore | None = None
    texture_score: NormalizedScore | None = None
    ripe_storage_score: NormalizedScore | None = None
    convenience_score: NormalizedScore | None = None
    is_default: bool
    is_active: bool
    display_order: Annotated[int, Field(ge=1)]
    data_quality: DataQuality
    data_source_note: Annotated[str, Field(max_length=500)] | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class FruitFactRead(ApiSchema):
    id: PositiveId
    fruit_id: PositiveId
    fact_type: FactType
    fact_text: Annotated[str, Field(min_length=1)]
    sort_order: Annotated[int, Field(ge=1)]
    is_active: bool
    source_note: Annotated[str, Field(max_length=500)] | None = None
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
    data_scope: SeasonDataScope = "legacy"
    data_quality: SeasonDataQuality = "unverified"
    cultivation_type: CultivationType = "unknown"
    source_note: Annotated[str, Field(max_length=2000)] | None = None
    source_year: Annotated[int, Field(ge=2000, le=2100)] | None = None
    is_scoring_enabled: bool = False


class FruitSeasonRead(FruitSeasonBase):
    id: PositiveId
    fruit_id: PositiveId
    created_at: AwareDatetime


class FruitDetail(FruitRead):
    nutrition: FruitNutritionRead | None = None
    seasons: list[FruitSeasonRead] = Field(default_factory=list)
    selection_options: list[FruitSelectionOptionRead] = Field(default_factory=list)


__all__ = [
    "FruitBase",
    "FruitDetail",
    "FruitFactRead",
    "FruitNutritionBase",
    "FruitNutritionRead",
    "FruitRead",
    "FruitSeasonBase",
    "FruitSeasonRead",
    "FruitSelectionOptionRead",
]
