from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
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
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.recommendation import RecommendationItem
    from app.models.user import UserFruitPreference


class Fruit(TimestampMixin, Base):
    __tablename__ = "fruits"
    __table_args__ = (
        UniqueConstraint("name", name="uq_fruits_name"),
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
            "convenience_score BETWEEN 0 AND 1",
            name="ck_fruits_convenience_score_range",
        ),
        CheckConstraint(
            "average_price_level BETWEEN 1 AND 3",
            name="ck_fruits_average_price_level_range",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
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
    convenience_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    average_price_level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    default_portion: Mapped[str] = mapped_column(String(80), nullable=False)
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
    seasons: Mapped[list[FruitSeason]] = relationship(
        back_populates="fruit",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    user_preferences: Mapped[list[UserFruitPreference]] = relationship(
        back_populates="fruit",
        passive_deletes="all",
    )
    recommendation_items: Mapped[list[RecommendationItem]] = relationship(
        back_populates="fruit",
        passive_deletes="all",
    )


class FruitNutrition(TimestampMixin, Base):
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
    __tablename__ = "fruit_seasons"
    __table_args__ = (
        UniqueConstraint(
            "fruit_id",
            "region",
            "start_month",
            "end_month",
            name="uq_fruit_seasons_fruit_region_months",
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
    start_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    end_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    season_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )

    fruit: Mapped[Fruit] = relationship(back_populates="seasons")
