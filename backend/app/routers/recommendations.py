"""今日推荐、刷新、历史和反馈路由。

所有路由依赖 ``CurrentUser``，因此 item/user 归属由服务层再次校验；
路由本身不实现评分，也不直接操作业务表。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.database import get_database_session
from app.schemas.recommendation import (
    RecommendationDetail,
    RecommendationFeedbackCreate,
    RecommendationFeedbackRead,
)
from app.services import recommendation_application_service


router = APIRouter(tags=["recommendations"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]
HistoryLimit = Annotated[int, Query(ge=1, le=100)]


@router.get(
    "/api/recommendations/today",
    response_model=RecommendationDetail,
)
def get_today_recommendation(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> RecommendationDetail:
    """返回当天 active 推荐，页面刷新不会无条件重新生成。"""
    return recommendation_application_service.get_today_recommendation(
        session,
        current_user.id,
    )


@router.post(
    "/api/recommendations/refresh",
    response_model=RecommendationDetail,
    status_code=status.HTTP_201_CREATED,
)
def refresh_recommendation(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> RecommendationDetail:
    """请求换组，旧记录由 Application Service 标记 replaced。"""
    return recommendation_application_service.refresh_recommendation(
        session,
        current_user.id,
    )


@router.get(
    "/api/me/recommendations",
    response_model=list[RecommendationDetail],
)
def list_current_user_recommendation_history(
    current_user: CurrentUser,
    session: DatabaseSession,
    limit: HistoryLimit = 30,
) -> list[RecommendationDetail]:
    """返回当前用户的分页上限内历史记录。"""
    return recommendation_application_service.list_recommendation_history(
        session,
        current_user.id,
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
    current_user: CurrentUser,
    session: DatabaseSession,
) -> RecommendationFeedbackRead:
    """提交单项反馈；重复同类型反馈返回 200 而不是重复插入。"""
    submission = recommendation_application_service.submit_feedback(
        session,
        item_id,
        payload,
        expected_user_id=current_user.id,
    )
    response.status_code = (
        status.HTTP_201_CREATED if submission.created else status.HTTP_200_OK
    )
    return submission.feedback


__all__ = ["router"]
