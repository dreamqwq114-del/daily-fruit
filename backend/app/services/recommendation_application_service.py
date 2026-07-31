from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.clock import current_app_date
from app.errors import ResourceConflictError, ResourceNotFoundError
from app.models import (
    Recommendation,
    RecommendationFeedback,
    RecommendationItem,
    User,
)
from app.repositories import (
    fruit_repository,
    recommendation_repository,
    user_repository,
)
from app.schemas.recommendation import (
    RecommendationDetail,
    RecommendationFeedbackCreate,
    RecommendationFeedbackRead,
)
from app.services.api_mapper import recommendation_to_detail
from app.services.recommendation_mapper import (
    build_recommendation_context,
    fruit_to_recommendation_input,
    user_to_recommendation_input,
)
from app.services.recommendation_service import (
    RecommendationError,
    recommend_fruits,
)
from app.services.recommendation_types import (
    RecommendationContext,
    RecommendationFruit,
    RecommendationResult,
    RecommendationUser,
)


HISTORY_DAYS = 7
FEEDBACK_DAYS = 30
DEFAULT_HISTORY_LIMIT = 30


@dataclass(frozen=True, slots=True)
class FeedbackSubmission:
    feedback: RecommendationFeedbackRead
    created: bool


def get_today_recommendation(
    session: Session,
    user_id: int,
    *,
    today: date | None = None,
) -> RecommendationDetail:
    recommendation_date = today or current_app_date()
    recommendation_repository.acquire_user_lock(session, user_id)
    user = user_repository.get_user(
        session,
        user_id,
        include_preferences=True,
    )
    if user is None:
        raise ResourceNotFoundError("用户不存在")

    existing = recommendation_repository.get_active_recommendation(
        session,
        user_id,
        recommendation_date,
    )
    if existing is not None:
        detail = recommendation_to_detail(existing)
        session.commit()
        return detail

    refresh_number = recommendation_repository.next_refresh_number(
        session,
        user_id,
        recommendation_date,
    )
    result = _calculate_recommendation(
        session,
        user,
        recommendation_date,
        refresh_number,
    )
    recommendation = _persist_recommendation(
        session,
        user_id,
        recommendation_date,
        refresh_number,
        result,
    )
    recommendation_id = recommendation.id
    session.commit()
    return _load_detail(session, recommendation_id)


def refresh_recommendation(
    session: Session,
    user_id: int,
    *,
    today: date | None = None,
) -> RecommendationDetail:
    recommendation_date = today or current_app_date()
    recommendation_repository.acquire_user_lock(session, user_id)
    user = user_repository.get_user(
        session,
        user_id,
        include_preferences=True,
    )
    if user is None:
        raise ResourceNotFoundError("用户不存在")

    active = recommendation_repository.get_active_recommendation(
        session,
        user_id,
        recommendation_date,
        for_update=True,
    )
    if active is None:
        raise ResourceConflictError("今天还没有可更换的 active 推荐")

    previous_ids = {item.fruit_id for item in active.items}
    active.status = "replaced"
    first_item = min(active.items, key=lambda item: item.rank)
    change_feedback = recommendation_repository.get_feedback(
        session,
        item_id=first_item.id,
        user_id=user_id,
        feedback_type="change_requested",
    )
    if change_feedback is None:
        recommendation_repository.add_feedback(
            session,
            RecommendationFeedback(
                recommendation_item_id=first_item.id,
                user_id=user_id,
                feedback_type="change_requested",
                comment=None,
            ),
        )
    session.flush()

    refresh_number = recommendation_repository.next_refresh_number(
        session,
        user_id,
        recommendation_date,
    )
    result = _calculate_recommendation(
        session,
        user,
        recommendation_date,
        refresh_number,
        previous_ids=previous_ids,
    )
    recommendation = _persist_recommendation(
        session,
        user_id,
        recommendation_date,
        refresh_number,
        result,
    )
    recommendation_id = recommendation.id
    session.commit()
    return _load_detail(session, recommendation_id)


def list_recommendation_history(
    session: Session,
    user_id: int,
    *,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[RecommendationDetail]:
    if user_repository.get_user(session, user_id) is None:
        raise ResourceNotFoundError("用户不存在")
    return [
        recommendation_to_detail(item)
        for item in recommendation_repository.list_history(
            session,
            user_id,
            limit=limit,
        )
    ]


def submit_feedback(
    session: Session,
    item_id: int,
    payload: RecommendationFeedbackCreate,
) -> FeedbackSubmission:
    item = recommendation_repository.get_item(session, item_id)
    if item is None:
        raise ResourceNotFoundError("推荐项不存在")
    user_id = item.recommendation.user_id
    existing = recommendation_repository.get_feedback(
        session,
        item_id=item_id,
        user_id=user_id,
        feedback_type=payload.feedback_type,
    )
    if existing is not None:
        return FeedbackSubmission(
            feedback=RecommendationFeedbackRead.model_validate(existing),
            created=False,
        )

    feedback = recommendation_repository.add_feedback(
        session,
        RecommendationFeedback(
            recommendation_item_id=item_id,
            user_id=user_id,
            feedback_type=payload.feedback_type,
            comment=payload.comment,
        ),
    )
    session.commit()
    return FeedbackSubmission(
        feedback=RecommendationFeedbackRead.model_validate(feedback),
        created=True,
    )


def _calculate_recommendation(
    session: Session,
    user: User,
    recommendation_date: date,
    refresh_number: int,
    *,
    previous_ids: set[int] | None = None,
) -> RecommendationResult:
    fruits = fruit_repository.list_active_fruits(session)
    domain_fruits = [
        fruit_to_recommendation_input(fruit) for fruit in fruits
    ]
    domain_user = user_to_recommendation_input(user)
    recent_ids = recommendation_repository.recent_fruit_ids(
        session,
        user.id,
        since=recommendation_date - timedelta(days=HISTORY_DAYS),
    )
    feedback = recommendation_repository.feedback_by_fruit(
        session,
        user.id,
        since=datetime.now(UTC) - timedelta(days=FEEDBACK_DAYS),
    )
    context = build_recommendation_context(
        month=recommendation_date.month,
        recent_fruit_ids=recent_ids,
        feedback_by_fruit=feedback,
        random_seed=_stable_seed(
            user.id,
            recommendation_date,
            refresh_number,
        ),
    )
    try:
        result = recommend_fruits(domain_fruits, domain_user, context)
    except RecommendationError as error:
        raise ResourceConflictError(str(error)) from error

    if previous_ids and _result_ids(result) == previous_ids:
        result = _different_pair_if_possible(
            domain_fruits,
            domain_user,
            context,
            previous_ids,
            fallback=result,
        )
    return result


def _different_pair_if_possible(
    fruits: list[RecommendationFruit],
    user: RecommendationUser,
    context: RecommendationContext,
    previous_ids: set[int],
    *,
    fallback: RecommendationResult,
) -> RecommendationResult:
    alternatives: list[RecommendationResult] = []
    for excluded_id in sorted(previous_ids):
        candidates = [
            fruit for fruit in fruits if fruit.id != excluded_id
        ]
        try:
            candidate = recommend_fruits(candidates, user, context)
        except RecommendationError:
            continue
        if _result_ids(candidate) != previous_ids:
            alternatives.append(candidate)
    return max(alternatives, key=lambda item: item.total_score, default=fallback)


def _persist_recommendation(
    session: Session,
    user_id: int,
    recommendation_date: date,
    refresh_number: int,
    result: RecommendationResult,
) -> Recommendation:
    recommendation = Recommendation(
        user_id=user_id,
        recommendation_date=recommendation_date,
        refresh_number=refresh_number,
        total_score=_score_decimal(result.total_score),
        status="active",
        items=[
            RecommendationItem(
                fruit_id=item.fruit.id,
                score=_score_decimal(item.score),
                rank=item.rank,
                reasons=[
                    reason.model_dump(mode="json")
                    for reason in item.reasons
                ],
            )
            for item in result.items
        ],
    )
    return recommendation_repository.add_recommendation(
        session,
        recommendation,
    )


def _load_detail(
    session: Session,
    recommendation_id: int,
) -> RecommendationDetail:
    session.expire_all()
    recommendation = recommendation_repository.get_recommendation(
        session,
        recommendation_id,
    )
    if recommendation is None:
        raise ResourceNotFoundError("推荐记录不存在")
    return recommendation_to_detail(recommendation)


def _stable_seed(
    user_id: int,
    recommendation_date: date,
    refresh_number: int,
) -> int:
    return (
        recommendation_date.toordinal() * 1_000_003
        + user_id * 101
        + refresh_number
    )


def _score_decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))


def _result_ids(result: RecommendationResult) -> set[int]:
    return {item.fruit.id for item in result.items}


__all__ = [
    "FeedbackSubmission",
    "get_today_recommendation",
    "list_recommendation_history",
    "refresh_recommendation",
    "submit_feedback",
]
