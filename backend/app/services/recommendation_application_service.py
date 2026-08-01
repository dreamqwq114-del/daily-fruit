"""推荐业务编排：加载数据、控制事务、调用纯算法并持久化结果。"""

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


HISTORY_DAYS = 30
FEEDBACK_DAYS = 180
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
    """复用当天 active 推荐；不存在时在用户锁内创建一组。"""

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
    """把旧组标记 replaced，记录换组事件并生成不同组合。"""

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
    """读取当前用户的推荐历史，具体预加载由 Repository 负责。"""

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
    *,
    expected_user_id: int | None = None,
) -> FeedbackSubmission:
    """校验 item 所属用户后幂等写入反馈，防止跨用户提交。"""

    item = recommendation_repository.get_item(session, item_id)
    if item is None:
        raise ResourceNotFoundError("推荐项不存在")
    user_id = item.recommendation.user_id
    if expected_user_id is not None and user_id != expected_user_id:
        raise ResourceNotFoundError("推荐项不存在")
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
    """把数据库快照组装成纯算法上下文，并转换领域错误为 API 冲突。"""

    fruits = fruit_repository.list_active_fruits(session)
    domain_fruits = [
        fruit_to_recommendation_input(fruit) for fruit in fruits
    ]
    domain_user = user_to_recommendation_input(user)
    since_date = recommendation_date - timedelta(days=HISTORY_DAYS)
    now = datetime.now(UTC)
    recent_ids = recommendation_repository.recent_fruit_ids(
        session,
        user.id,
        since=since_date,
        until=recommendation_date,
    )
    history_events = recommendation_repository.history_events(
        session,
        user.id,
        since=since_date,
        until=recommendation_date,
    )
    previous_pairs = recommendation_repository.previous_pairs(
        session,
        user.id,
        since=since_date,
        until=recommendation_date,
    )
    feedback_events = recommendation_repository.feedback_events(
        session,
        user.id,
        since=now - timedelta(days=FEEDBACK_DAYS),
        until=now,
    )
    feedback = recommendation_repository.feedback_by_fruit(
        session,
        user.id,
        since=now - timedelta(days=FEEDBACK_DAYS),
        until=now,
    )
    context = build_recommendation_context(
        month=recommendation_date.month,
        today=recommendation_date,
        recent_fruit_ids=recent_ids,
        feedback_by_fruit=feedback,
        history_events=history_events,
        feedback_events=feedback_events,
        previous_pairs=previous_pairs,
        excluded_pair=(
            frozenset(previous_ids) if previous_ids else None
        ),
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
    """刷新后若仍返回原组合，尝试排除其中一个水果寻找替代组。"""

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
    """把算法结果和 JSONB reasons 映射为 ORM，等待外层事务提交。"""

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
                individual_score=_score_decimal(
                    item.individual_score
                    if item.individual_score is not None
                    else item.score
                ),
                pair_score=_score_decimal(
                    item.pair_score
                    if item.pair_score is not None
                    else result.total_score
                ),
                nutrition_pair_score=_score_decimal(
                    item.nutrition_pair_score
                    if item.nutrition_pair_score is not None
                    else 0
                ),
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
    """提交后重新加载完整水果/反馈关系，生成 API 详情。"""

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
    """由用户、日期和刷新序号构成可复现的近优组合 seed。"""

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
