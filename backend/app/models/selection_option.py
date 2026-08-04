"""父水果下可购买消费类型及用户类型偏好 ORM。

消费类型不是新的顶层水果。它们只在父水果已经入选后，为口感字段提供
一个真实、可回看的解析档案；用户偏好表只保存明确的 liked/disliked，
没有记录即表示 unknown。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.fruit import Fruit
    from app.models.user import User


class FruitSelectionOption(TimestampMixin, Base):
    """一个父水果下的稳定消费类型选项。"""

    __tablename__ = "fruit_selection_options"
    __table_args__ = (
        UniqueConstraint("fruit_id", "code", name="uq_fruit_selection_options_fruit_code"),
        # The second unique key is the target of the composite FK below.
        UniqueConstraint("fruit_id", "id", name="uq_fruit_selection_options_fruit_id_id"),
        CheckConstraint(
            "sweet_score IS NULL OR sweet_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_sweet_range",
        ),
        CheckConstraint(
            "sour_score IS NULL OR sour_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_sour_range",
        ),
        CheckConstraint(
            "soft_score IS NULL OR soft_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_soft_range",
        ),
        CheckConstraint(
            "crisp_score IS NULL OR crisp_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_crisp_range",
        ),
        CheckConstraint(
            "texture_score IS NULL OR texture_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_texture_range",
        ),
        CheckConstraint(
            "ripe_storage_score IS NULL OR ripe_storage_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_ripe_range",
        ),
        CheckConstraint(
            "convenience_score IS NULL OR convenience_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_convenience_range",
        ),
        CheckConstraint(
            "ripe_storage_score IS NULL OR ripe_storage_score IN "
            "(0.10, 0.30, 0.50, 0.70, 0.90)",
            name="ck_fruit_selection_options_ripe_storage_values",
        ),
        CheckConstraint(
            "legacy_score_snapshot IS NULL OR "
            "jsonb_typeof(legacy_score_snapshot) = 'object'",
            name="ck_fruit_selection_options_legacy_score_snapshot_object",
        ),
        CheckConstraint(
            "is_default = false OR (sweet_score IS NULL AND sour_score IS NULL "
            "AND soft_score IS NULL AND crisp_score IS NULL AND texture_score IS NULL "
            "AND ripe_storage_score IS NULL AND convenience_score IS NULL)",
            name="ck_fruit_selection_options_default_overrides_null",
        ),
        CheckConstraint(
            "is_default = false OR is_active = true",
            name="ck_fruit_selection_options_default_active",
        ),
        CheckConstraint(
            "display_order > 0",
            name="ck_fruit_selection_options_display_order_positive",
        ),
        Index(
            "ix_fruit_selection_options_fruit_active_order",
            "fruit_id",
            "is_active",
            "display_order",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    fruit_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.fruits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sweet_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    sour_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    soft_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    crisp_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    texture_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    ripe_storage_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    convenience_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    legacy_score_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    display_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1")
    )
    data_quality: Mapped[str] = mapped_column(
        String(20), nullable=False, default="low", server_default=text("'low'")
    )
    data_source_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    fruit: Mapped[Fruit] = relationship(back_populates="selection_options")
    user_preferences: Mapped[list[UserFruitOptionPreference]] = relationship(
        back_populates="option",
        passive_deletes="all",
    )


Index(
    "uq_fruit_selection_options_active_default",
    FruitSelectionOption.fruit_id,
    unique=True,
    postgresql_where=text("is_default IS TRUE AND is_active IS TRUE"),
)


class UserFruitOptionPreference(TimestampMixin, Base):
    """用户对某个父水果消费类型的明确偏好。"""

    __tablename__ = "user_fruit_option_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "option_id",
            name="uq_user_fruit_option_preferences_user_option",
        ),
        ForeignKeyConstraint(
            ["fruit_id", "option_id"],
            [
                "public.fruit_selection_options.fruit_id",
                "public.fruit_selection_options.id",
            ],
            name="fk_user_fruit_option_preferences_fruit_option",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "preference IN ('liked', 'disliked')",
            name="ck_user_fruit_option_preferences_preference_values",
        ),
        Index(
            "ix_user_fruit_option_preferences_user_fruit",
            "user_id",
            "fruit_id",
        ),
        Index("ix_user_fruit_option_preferences_fruit_id", "fruit_id"),
        Index("ix_user_fruit_option_preferences_option_id", "option_id"),
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
    fruit_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    option_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    preference: Mapped[str] = mapped_column(String(16), nullable=False)

    user: Mapped[User] = relationship(back_populates="fruit_option_preferences")
    option: Mapped[FruitSelectionOption] = relationship(
        back_populates="user_preferences"
    )


__all__ = ["FruitSelectionOption", "UserFruitOptionPreference"]
