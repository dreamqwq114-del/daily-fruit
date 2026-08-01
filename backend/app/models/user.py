from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    SmallInteger,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


AUTH_USERS_TABLE = Table(
    "users",
    Base.metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    schema="auth",
    info={"external": True},
)

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
            "sweet_preference IS NULL OR sweet_preference BETWEEN 0 AND 1",
            name="ck_users_sweet_preference_range",
        ),
        CheckConstraint(
            "sour_preference IS NULL OR sour_preference BETWEEN 0 AND 1",
            name="ck_users_sour_preference_range",
        ),
        CheckConstraint(
            "soft_preference IS NULL OR soft_preference BETWEEN 0 AND 1",
            name="ck_users_soft_preference_range",
        ),
        CheckConstraint(
            "crisp_preference IS NULL OR crisp_preference BETWEEN 0 AND 1",
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
        CheckConstraint(
            "discovery_level BETWEEN 0 AND 2",
            name="ck_users_discovery_level_range",
        ),
        CheckConstraint(
            "consumption_horizon_days IN (2, 4, 7)",
            name="ck_users_consumption_horizon_days_values",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    auth_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    sweet_preference: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
    )
    sour_preference: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
    )
    soft_preference: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
    )
    crisp_preference: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
    )
    price_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    convenience_preference: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )
    discovery_level: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    consumption_horizon_days: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=4,
        server_default=text("4"),
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
            "preference_score IS NULL OR preference_score BETWEEN -1 AND 2",
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
    preference_score: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2),
        nullable=True,
    )
    is_forbidden: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    has_tried: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    willing_to_try: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    user: Mapped[User] = relationship(back_populates="fruit_preferences")
    fruit: Mapped[Fruit] = relationship(back_populates="user_preferences")
