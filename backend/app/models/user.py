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
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.fruit import Fruit
    from app.models.recommendation import (
        Recommendation,
        RecommendationFeedback,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "sweet_preference BETWEEN 0 AND 1",
            name="ck_users_sweet_preference_range",
        ),
        CheckConstraint(
            "sour_preference BETWEEN 0 AND 1",
            name="ck_users_sour_preference_range",
        ),
        CheckConstraint(
            "soft_preference BETWEEN 0 AND 1",
            name="ck_users_soft_preference_range",
        ),
        CheckConstraint(
            "crisp_preference BETWEEN 0 AND 1",
            name="ck_users_crisp_preference_range",
        ),
        CheckConstraint(
            "convenience_preference BETWEEN 0 AND 1",
            name="ck_users_convenience_preference_range",
        ),
        CheckConstraint(
            "price_level BETWEEN 1 AND 3",
            name="ck_users_price_level_range",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    sweet_preference: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    sour_preference: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    soft_preference: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    crisp_preference: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    price_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    convenience_preference: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )

    fruit_preferences: Mapped[list[UserFruitPreference]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="user",
        passive_deletes="all",
    )
    recommendation_feedback: Mapped[list[RecommendationFeedback]] = (
        relationship(
            back_populates="user",
            passive_deletes="all",
        )
    )


class UserFruitPreference(TimestampMixin, Base):
    __tablename__ = "user_fruit_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "fruit_id",
            name="uq_user_fruit_preferences_user_fruit",
        ),
        CheckConstraint(
            "preference_score BETWEEN -1 AND 2",
            name="ck_user_fruit_preferences_score_range",
        ),
        Index(
            "ix_user_fruit_preferences_fruit_id",
            "fruit_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    fruit_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.fruits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    preference_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )
    is_forbidden: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    user: Mapped[User] = relationship(back_populates="fruit_preferences")
    fruit: Mapped[Fruit] = relationship(back_populates="user_preferences")
