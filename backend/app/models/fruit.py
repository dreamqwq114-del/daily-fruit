"""水果目录、营养和地区季节窗口 ORM。

Fruit 是推荐候选的身份数据；nutrition 和 seasons 通过外键关系加载。
``is_active`` 用于停用而不是删除历史水果，避免 recommendation_items 变成
孤立记录。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    ARRAY,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.recommendation import RecommendationItem
    from app.models.selection_option import FruitSelectionOption
    from app.models.user import UserFruitPreference


class Fruit(TimestampMixin, Base):
    """水果身份、口感、价格、便利性与推荐角色。"""

    __tablename__ = "fruits"
    __table_args__ = (
        UniqueConstraint("name", name="uq_fruits_name"),
        UniqueConstraint("code", name="uq_fruits_code"),
        CheckConstraint(
            "sweet_score BETWEEN 0 AND 1",
            name="ck_fruits_sweet_score_range",
        ),
        CheckConstraint(
            "sour_score BETWEEN 0 AND 1",
            name="ck_fruits_sour_score_range",
        ),
        CheckConstraint(
            "soft_score BETWEEN 0 AND 1",
            name="ck_fruits_soft_score_range",
        ),
        CheckConstraint(
            "crisp_score BETWEEN 0 AND 1",
            name="ck_fruits_crisp_score_range",
        ),
        CheckConstraint(
            "texture_score BETWEEN 0 AND 1",
            name="ck_fruits_texture_score_range",
        ),
        CheckConstraint(
            "ripe_storage_score IN (0.10, 0.30, 0.50, 0.70, 0.90)",
            name="ck_fruits_ripe_storage_score_values",
        ),
        CheckConstraint(
            "convenience_score BETWEEN 0 AND 1",
            name="ck_fruits_convenience_score_range",
        ),
        CheckConstraint(
            "average_price_level BETWEEN 1 AND 3",
            name="ck_fruits_average_price_level_range",
        ),
        CheckConstraint(
            "default_portion_grams > 0",
            name="ck_fruits_default_portion_grams_positive",
        ),
        CheckConstraint(
            "preparation_difficulty BETWEEN 0 AND 1",
            name="ck_fruits_preparation_difficulty_range",
        ),
        CheckConstraint(
            "portability_score BETWEEN 0 AND 1",
            name="ck_fruits_portability_score_range",
        ),
        CheckConstraint(
            "messiness_score BETWEEN 0 AND 1",
            name="ck_fruits_messiness_score_range",
        ),
        CheckConstraint(
            "storage_difficulty BETWEEN 0 AND 1",
            name="ck_fruits_storage_difficulty_range",
        ),
        CheckConstraint(
            "aroma_intensity BETWEEN 0 AND 1",
            name="ck_fruits_aroma_intensity_range",
        ),
        CheckConstraint(
            "commonness_score BETWEEN 0 AND 1",
            name="ck_fruits_commonness_score_range",
        ),
        CheckConstraint(
            "novelty_level BETWEEN 0 AND 2",
            name="ck_fruits_novelty_level_range",
        ),
        CheckConstraint(
            "consumption_mode IN ('direct', 'peel', 'cut', 'ingredient')",
            name="ck_fruits_consumption_mode_values",
        ),
        CheckConstraint(
            "daily_recommendation_role IN ('main', 'supporting')",
            name="ck_fruits_daily_role_values",
        ),
        CheckConstraint(
            "data_quality IN ('high', 'medium', 'low')",
            name="ck_fruits_data_quality_values",
        ),
        CheckConstraint(
            "typical_purchase_stage IN ('ready_to_eat', 'needs_ripening', 'variable')",
            name="ck_fruits_typical_purchase_stage_values",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    code: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar[]"),
    )
    # Deprecated compatibility grouping.  Recommendation scoring must not
    # read this presentation-oriented field.
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    display_group: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    taste: Mapped[str] = mapped_column(String(120), nullable=False)
    sweet_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    sour_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    soft_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    crisp_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    texture_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    convenience_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    ripe_storage_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    typical_purchase_stage: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    ripening_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    average_price_level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    default_portion: Mapped[str] = mapped_column(String(80), nullable=False)
    default_portion_grams: Mapped[Decimal] = mapped_column(
        Numeric(7, 2),
        nullable=False,
        default=Decimal("100"),
        server_default=text("100"),
    )
    direct_eating: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    consumption_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="direct",
        server_default=text("'direct'"),
    )
    daily_recommendation_role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="main",
        server_default=text("'main'"),
    )
    preparation_difficulty: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.5"),
        server_default=text("0.5"),
    )
    portability_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.5"),
        server_default=text("0.5"),
    )
    messiness_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.5"),
        server_default=text("0.5"),
    )
    storage_difficulty: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.5"),
        server_default=text("0.5"),
    )
    aroma_intensity: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.5"),
        server_default=text("0.5"),
    )
    commonness_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.5"),
        server_default=text("0.5"),
    )
    novelty_level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    data_quality: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="low",
        server_default=text("'low'"),
    )
    data_source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    nutrition: Mapped[FruitNutrition | None] = relationship(
        back_populates="fruit",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )
    facts: Mapped[list[FruitFact]] = relationship(
        back_populates="fruit",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="FruitFact.sort_order",
    )
    seasons: Mapped[list[FruitSeason]] = relationship(
        back_populates="fruit",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="FruitSeason.id",
    )
    user_preferences: Mapped[list[UserFruitPreference]] = relationship(
        back_populates="fruit",
        passive_deletes="all",
    )
    selection_options: Mapped[list[FruitSelectionOption]] = relationship(
        back_populates="fruit",
        passive_deletes="all",
        order_by="FruitSelectionOption.display_order",
    )
    recommendation_items: Mapped[list[RecommendationItem]] = relationship(
        back_populates="fruit",
        passive_deletes="all",
    )


class FruitFact(TimestampMixin, Base):
    """姘存灉鍐锋煡鏂囨锛氭瘡绉嶆按鏋滃彲淇濆瓨澶氭潯骞舵寜鏃ユ湡杞崲銆?"""

    __tablename__ = "fruit_facts"
    __table_args__ = (
        UniqueConstraint(
            "fruit_id",
            "sort_order",
            name="uq_fruit_facts_fruit_sort_order",
        ),
        CheckConstraint(
            "sort_order > 0",
            name="ck_fruit_facts_sort_order_positive",
        ),
        CheckConstraint(
            "length(btrim(fact_type)) > 0",
            name="ck_fruit_facts_fact_type_not_blank",
        ),
        CheckConstraint(
            "length(btrim(fact_text)) > 0",
            name="ck_fruit_facts_fact_text_not_blank",
        ),
        Index(
            "ix_fruit_facts_fruit_active",
            "fruit_id",
            "is_active",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    fruit_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.fruits.id", ondelete="CASCADE"),
        nullable=False,
    )
    fact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    fruit: Mapped[Fruit] = relationship(back_populates="facts")


class FruitNutrition(TimestampMixin, Base):
    """每种水果唯一的营养演示行；当前源数据是无单位归一化分数。"""

    __tablename__ = "fruit_nutritions"
    __table_args__ = (
        UniqueConstraint("fruit_id", name="uq_fruit_nutritions_fruit_id"),
        CheckConstraint(
            "energy >= 0",
            name="ck_fruit_nutritions_energy_nonnegative",
        ),
        CheckConstraint(
            "vitamin_c >= 0",
            name="ck_fruit_nutritions_vitamin_c_nonnegative",
        ),
        CheckConstraint(
            "fiber >= 0",
            name="ck_fruit_nutritions_fiber_nonnegative",
        ),
        CheckConstraint(
            "potassium >= 0",
            name="ck_fruit_nutritions_potassium_nonnegative",
        ),
        CheckConstraint(
            "folate >= 0",
            name="ck_fruit_nutritions_folate_nonnegative",
        ),
        CheckConstraint(
            "carotenoids >= 0",
            name="ck_fruit_nutritions_carotenoids_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    fruit_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.fruits.id", ondelete="CASCADE"),
        nullable=False,
    )
    energy: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vitamin_c: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fiber: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    potassium: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    folate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    carotenoids: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    fruit: Mapped[Fruit] = relationship(back_populates="nutrition")


class FruitSeason(CreatedAtMixin, Base):
    """水果的地区/月度季节和供应窗口，支持跨年月份。"""

    __tablename__ = "fruit_seasons"
    __table_args__ = (
        UniqueConstraint(
            "fruit_id",
            "data_scope",
            "region",
            "start_month",
            "end_month",
            name="uq_fruit_seasons_fruit_scope_region_months",
        ),
        CheckConstraint(
            "region_level IN ('city', 'province', 'area', 'national')",
            name="ck_fruit_seasons_region_level_values",
        ),
        CheckConstraint(
            "availability_score BETWEEN 0 AND 1",
            name="ck_fruit_seasons_availability_score_range",
        ),
        CheckConstraint(
            "supply_status IN ('available', 'unknown', 'unavailable')",
            name="ck_fruit_seasons_supply_status_values",
        ),
        CheckConstraint(
            "data_scope IN ('harvest', 'market', 'legacy')",
            name="ck_fruit_seasons_data_scope_values",
        ),
        CheckConstraint(
            "data_quality IN ('high', 'medium', 'low', 'unverified')",
            name="ck_fruit_seasons_data_quality_values",
        ),
        CheckConstraint(
            "cultivation_type IN ('open_field', 'protected', 'mixed', 'unknown')",
            name="ck_fruit_seasons_cultivation_type_values",
        ),
        CheckConstraint(
            "source_year IS NULL OR source_year BETWEEN 2000 AND 2100",
            name="ck_fruit_seasons_source_year_range",
        ),
        CheckConstraint(
            "source_note IS NULL OR length(source_note) <= 2000",
            name="ck_fruit_seasons_source_note_length",
        ),
        CheckConstraint(
            "(region = '全国') = (region_level = 'national')",
            name="ck_fruit_seasons_region_level_contract",
        ),
        CheckConstraint(
            "NOT is_scoring_enabled OR (data_scope <> 'legacy' "
            "AND data_quality IN ('high', 'medium') AND source_note IS NOT NULL "
            "AND length(btrim(source_note)) > 0 AND source_year IS NOT NULL)",
            name="ck_fruit_seasons_scoring_evidence",
        ),
        CheckConstraint(
            "data_scope <> 'legacy' OR NOT is_scoring_enabled",
            name="ck_fruit_seasons_legacy_disabled",
        ),
        CheckConstraint(
            "data_scope = 'legacy' OR data_quality <> 'unverified' "
            "OR supply_status <> 'available'",
            name="ck_fruit_seasons_unverified_supply",
        ),
        CheckConstraint(
            "data_scope = 'legacy' OR "
            "(data_scope = 'harvest' AND availability_score = 0.45 "
            "AND supply_status = 'unknown') OR "
            "(data_scope = 'market' AND season_score = 0.35 "
            "AND cultivation_type = 'unknown')",
            name="ck_fruit_seasons_scope_semantics",
        ),
        CheckConstraint(
            "start_month BETWEEN 1 AND 12",
            name="ck_fruit_seasons_start_month_range",
        ),
        CheckConstraint(
            "end_month BETWEEN 1 AND 12",
            name="ck_fruit_seasons_end_month_range",
        ),
        CheckConstraint(
            "season_score BETWEEN 0 AND 1",
            name="ck_fruit_seasons_score_range",
        ),
        Index(
            "ix_fruit_seasons_region_fruit_id",
            "region",
            "fruit_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    fruit_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.fruits.id", ondelete="CASCADE"),
        nullable=False,
    )
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    region_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="national",
        server_default=text("'national'"),
    )
    start_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    end_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    season_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    availability_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("0.45"),
        server_default=text("0.45"),
    )
    supply_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unknown",
        server_default=text("'unknown'"),
    )
    data_scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="legacy",
        server_default=text("'legacy'"),
    )
    data_quality: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unverified",
        server_default=text("'unverified'"),
    )
    cultivation_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unknown",
        server_default=text("'unknown'"),
    )
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_scoring_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    fruit: Mapped[Fruit] = relationship(back_populates="seasons")
