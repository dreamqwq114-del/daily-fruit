"""Authenticated product feedback HTTP endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.database import get_database_session
from app.schemas.product_feedback import (
    ProductFeedbackCreate,
    ProductFeedbackRead,
)
from app.services import product_feedback_service


router = APIRouter(tags=["product-feedback"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post(
    "/api/product-feedback",
    response_model=ProductFeedbackRead,
    status_code=status.HTTP_201_CREATED,
)
def create_product_feedback(
    payload: ProductFeedbackCreate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> ProductFeedbackRead:
    """Create one plain-text product message for the current business user."""

    return product_feedback_service.create_product_feedback(
        session,
        current_user.id,
        payload,
    )


__all__ = ["router"]
