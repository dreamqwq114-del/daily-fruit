"""推荐、推荐项和用户反馈 ORM。

Recommendation 保存一次组合的日期、刷新序号和状态；items 保存评分、
结构化理由和水果快照关联；feedback 通过 item 与 user 双外键保护归属。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.fruit import Fruit
    from app.models.selection_option import FruitSelectionOption
    from app.models.user import User


class Recommendation(CreatedAtMixin, Base):
    """一组推荐及其 active/replaced 生命周期。"""

    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "recommendation_date",
            "refresh_number",
            name="uq_recommendations_user_date_refresh",
        ),
        CheckConstraint(
            "refresh_number >= 0",
            name="ck_recommendations_refresh_number_nonnegative",
        ),
        CheckConstraint(
            "total_score BETWEEN 0 AND 1",
            name="ck_recommendations_total_score_range",
        ),
        CheckConstraint(
            "status IN ('active', 'replaced')",
            name="ck_recommendations_status_values",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recommendation_date: Mapped[date] = mapped_column(Date, nullable=False)
    refresh_number: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    user: Mapped[User] = relationship(back_populates="recommendations")
    items: Mapped[list[RecommendationItem]] = relationship(
        back_populates="recommendation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


Index(
    "uq_recommendations_active_user_date",
    Recommendation.user_id,
    Recommendation.recommendation_date,
    unique=True,
    postgresql_where=text("status = 'active'"),
)
Index(
    "ix_recommendations_user_history",
    Recommendation.user_id,
    Recommendation.recommendation_date.desc(),
    Recommendation.refresh_number.desc(),
)


class RecommendationItem(CreatedAtMixin, Base):
    """推荐中的一个水果，rank 保证一组最多按 1/2 排列。"""

    __tablename__ = "recommendation_items"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_id",
            "rank",
            name="uq_recommendation_items_recommendation_rank",
        ),
        UniqueConstraint(
            "recommendation_id",
            "fruit_id",
            name="uq_recommendation_items_recommendation_fruit",
        ),
        CheckConstraint(
            "score BETWEEN 0 AND 1",
            name="ck_recommendation_items_score_range",
        ),
        CheckConstraint(
            "individual_score BETWEEN 0 AND 1",
            name="ck_recommendation_items_individual_score_range",
        ),
        CheckConstraint(
            "pair_score BETWEEN 0 AND 1",
            name="ck_recommendation_items_pair_score_range",
        ),
        CheckConstraint(
            "nutrition_pair_score BETWEEN 0 AND 1",
            name="ck_recommendation_items_nutrition_pair_score_range",
        ),
        CheckConstraint(
            "rank IN (1, 2)",
            name="ck_recommendation_items_rank_values",
        ),
        CheckConstraint(
            "jsonb_typeof(reasons) = 'array'",
            name="ck_recommendation_items_reasons_array",
        ),
        CheckConstraint(
            "selection_resolution_source IS NULL OR selection_resolution_source IN "
            "('explicit', 'inferred_from_global_preference', 'default', 'not_applicable')",
            name="ck_recommendation_items_selection_resolution_source",
        ),
        CheckConstraint(
            "effective_sweet_score_snapshot IS NULL OR effective_sweet_score_snapshot BETWEEN 0 AND 1",
            name="ck_recommendation_items_selection_sweet_range",
        ),
        CheckConstraint(
            "effective_sour_score_snapshot IS NULL OR effective_sour_score_snapshot BETWEEN 0 AND 1",
            name="ck_recommendation_items_selection_sour_range",
        ),
        CheckConstraint(
            "effective_soft_score_snapshot IS NULL OR effective_soft_score_snapshot BETWEEN 0 AND 1",
            name="ck_recommendation_items_selection_soft_range",
        ),
        CheckConstraint(
            "effective_crisp_score_snapshot IS NULL OR effective_crisp_score_snapshot BETWEEN 0 AND 1",
            name="ck_recommendation_items_selection_crisp_range",
        ),
        Index(
            "ix_recommendation_items_fruit_id",
            "fruit_id",
        ),
        Index(
            "ix_recommendation_items_selection_option_id",
            "selection_option_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    recommendation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.recommendations.id", ondelete="CASCADE"),
        nullable=False,
    )
    fruit_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.fruits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    individual_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
    )
    pair_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
    )
    nutrition_pair_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    selection_option_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "public.fruit_selection_options.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    selection_option_name_snapshot: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    selection_option_code_snapshot: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )
    selection_resolution_source: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )
    effective_sweet_score_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3), nullable=True
    )
    effective_sour_score_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3), nullable=True
    )
    effective_soft_score_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3), nullable=True
    )
    effective_crisp_score_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3), nullable=True
    )

    recommendation: Mapped[Recommendation] = relationship(
        back_populates="items"
    )
    fruit: Mapped[Fruit] = relationship(back_populates="recommendation_items")
    selection_option: Mapped[FruitSelectionOption | None] = relationship(
        passive_deletes="all"
    )
    feedback: Mapped[list[RecommendationFeedback]] = relationship(
        back_populates="recommendation_item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RecommendationFeedback(CreatedAtMixin, Base):
    """用户对推荐项的幂等反馈事件。"""

    __tablename__ = "recommendation_feedback"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_item_id",
            "user_id",
            "feedback_type",
            name="uq_recommendation_feedback_item_user_type",
        ),
        CheckConstraint(
            (
                "feedback_type IN ("
                "'eaten', 'liked', 'disliked', 'unavailable', "
                "'expensive', 'tired_of_it', 'change_requested'"
                ")"
            ),
            name="ck_recommendation_feedback_type_values",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    recommendation_item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "public.recommendation_items.id",
            ondelete="CASCADE",
            name="fk_rec_feedback_item_id_items",
        ),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    recommendation_item: Mapped[RecommendationItem] = relationship(
        back_populates="feedback"
    )
    user: Mapped[User] = relationship(
        back_populates="recommendation_feedback"
    )


Index(
    "ix_recommendation_feedback_user_created_at",
    RecommendationFeedback.user_id,
    RecommendationFeedback.created_at.desc(),
)
