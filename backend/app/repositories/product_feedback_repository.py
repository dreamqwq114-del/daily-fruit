"""Persistence primitives for product feedback."""

from sqlalchemy.orm import Session

from app.models import ProductFeedback


def add_product_feedback(
    session: Session,
    feedback: ProductFeedback,
) -> ProductFeedback:
    """Add and flush a feedback row so its identity is available immediately."""

    session.add(feedback)
    session.flush()
    return feedback


__all__ = ["add_product_feedback"]
