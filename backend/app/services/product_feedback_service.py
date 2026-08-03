"""Business service for authenticated product feedback submissions."""

from sqlalchemy.orm import Session

from app.models import ProductFeedback
from app.repositories import product_feedback_repository
from app.schemas.product_feedback import (
    ProductFeedbackCreate,
    ProductFeedbackRead,
)


def create_product_feedback(
    session: Session,
    user_id: int,
    payload: ProductFeedbackCreate,
) -> ProductFeedbackRead:
    """Persist a product message owned by the already-authorized user.

    ``user_id`` is supplied by ``CurrentUser`` in the router, never by the
    request body.  Commit and rollback behavior follows the existing service
    convention; database failures are handled by the application error layer.
    """

    feedback = ProductFeedback(
        user_id=user_id,
        category=payload.category,
        content=payload.content,
        page_key=payload.page_key,
    )
    product_feedback_repository.add_product_feedback(session, feedback)
    session.commit()
    return ProductFeedbackRead.model_validate(feedback)


__all__ = ["create_product_feedback"]
