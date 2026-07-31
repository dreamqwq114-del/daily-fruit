from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.schemas.recommendation import (
    RecommendationDetail,
    RecommendationFeedbackCreate,
    RecommendationFeedbackRead,
    RecommendationRefreshRequest,
)
from app.services import recommendation_application_service


router = APIRouter(tags=["recommendations"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]
PositiveUserId = Annotated[int, Query(gt=0)]
HistoryLimit = Annotated[int, Query(ge=1, le=100)]


@router.get(
    "/api/recommendations/today",
    response_model=RecommendationDetail,
)
def get_today_recommendation(
    user_id: PositiveUserId,
    session: DatabaseSession,
) -> RecommendationDetail:
    return recommendation_application_service.get_today_recommendation(
        session,
        user_id,
    )


@router.post(
    "/api/recommendations/refresh",
    response_model=RecommendationDetail,
    status_code=status.HTTP_201_CREATED,
)
def refresh_recommendation(
    payload: RecommendationRefreshRequest,
    session: DatabaseSession,
) -> RecommendationDetail:
    return recommendation_application_service.refresh_recommendation(
        session,
        payload.user_id,
    )


@router.get(
    "/api/users/{user_id}/recommendations",
    response_model=list[RecommendationDetail],
)
def list_recommendation_history(
    user_id: int,
    session: DatabaseSession,
    limit: HistoryLimit = 30,
) -> list[RecommendationDetail]:
    return recommendation_application_service.list_recommendation_history(
        session,
        user_id,
        limit=limit,
    )


@router.post(
    "/api/recommendations/items/{item_id}/feedback",
    response_model=RecommendationFeedbackRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    item_id: int,
    payload: RecommendationFeedbackCreate,
    response: Response,
    session: DatabaseSession,
) -> RecommendationFeedbackRead:
    submission = recommendation_application_service.submit_feedback(
        session,
        item_id,
        payload,
    )
    response.status_code = (
        status.HTTP_201_CREATED if submission.created else status.HTTP_200_OK
    )
    return submission.feedback


__all__ = ["router"]
