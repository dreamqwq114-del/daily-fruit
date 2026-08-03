"""Product feedback persistence model.

Product feedback is intentionally separate from recommendation feedback.  It
records product-level suggestions and bug reports submitted by authenticated
users; it never changes a user's fruit preferences or recommendation scores.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.user import User


class ProductFeedback(CreatedAtMixin, Base):
    """A plain-text product suggestion or issue from an authenticated user."""

    __tablename__ = "product_feedback"
    __table_args__ = (
        CheckConstraint(
            "category IN ("
            "'recommendation_quality', 'suggestion', 'bug', "
            "'fruit_content', 'other'"
            ")",
            name="ck_product_feedback_category_values",
        ),
        CheckConstraint(
            "char_length(btrim(content)) BETWEEN 1 AND 1000",
            name="ck_product_feedback_content_length",
        ),
        CheckConstraint(
            "page_key IS NULL OR page_key IN "
            "('today', 'preferences', 'history')",
            name="ck_product_feedback_page_key_values",
        ),
        CheckConstraint(
            "status IN ('new', 'resolved')",
            name="ck_product_feedback_status_values",
        ),
        CheckConstraint(
            "(status = 'new' AND resolved_at IS NULL) OR "
            "(status = 'resolved' AND resolved_at IS NOT NULL)",
            name="ck_product_feedback_status_resolved_at_consistency",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("public.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    page_key: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="new",
        server_default=text("'new'"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


Index(
    "ix_product_feedback_status_created_at",
    ProductFeedback.status,
    ProductFeedback.created_at.desc(),
)
Index("ix_product_feedback_user_id", ProductFeedback.user_id)


__all__ = ["ProductFeedback"]
