from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Fruit,
    Recommendation,
    RecommendationFeedback,
    RecommendationItem,
)
from app.services.recommendation_types import FeedbackEvent, HistoryEvent


RECOMMENDATION_DETAIL_OPTIONS = (
    selectinload(Recommendation.items)
    .selectinload(RecommendationItem.fruit)
    .selectinload(Fruit.nutrition),
    selectinload(Recommendation.items)
    .selectinload(RecommendationItem.fruit)
    .selectinload(Fruit.seasons),
    selectinload(Recommendation.items).selectinload(
        RecommendationItem.feedback
    ),
)


def acquire_user_lock(session: Session, user_id: int) -> None:
    session.execute(select(func.pg_advisory_xact_lock(user_id)))


def get_active_recommendation(
    session: Session,
    user_id: int,
    recommendation_date: date,
    *,
    for_update: bool = False,
) -> Recommendation | None:
    statement = (
        select(Recommendation)
        .where(
            Recommendation.user_id == user_id,
            Recommendation.recommendation_date == recommendation_date,
            Recommendation.status == "active",
        )
        .options(*RECOMMENDATION_DETAIL_OPTIONS)
    )
    if for_update:
        statement = statement.with_for_update()
    return session.execute(statement).scalar_one_or_none()


def get_recommendation(
    session: Session,
    recommendation_id: int,
) -> Recommendation | None:
    statement = (
        select(Recommendation)
        .where(Recommendation.id == recommendation_id)
        .options(*RECOMMENDATION_DETAIL_OPTIONS)
    )
    return session.execute(statement).scalar_one_or_none()


def list_history(
    session: Session,
    user_id: int,
    *,
    limit: int,
) -> list[Recommendation]:
    statement = (
        select(Recommendation)
        .where(Recommendation.user_id == user_id)
        .options(*RECOMMENDATION_DETAIL_OPTIONS)
        .order_by(
            Recommendation.recommendation_date.desc(),
            Recommendation.refresh_number.desc(),
            Recommendation.id.desc(),
        )
        .limit(limit)
    )
    return list(session.execute(statement).scalars())


def next_refresh_number(
    session: Session,
    user_id: int,
    recommendation_date: date,
) -> int:
    statement = select(
        func.coalesce(func.max(Recommendation.refresh_number), -1) + 1
    ).where(
        Recommendation.user_id == user_id,
        Recommendation.recommendation_date == recommendation_date,
    )
    return int(session.execute(statement).scalar_one())


def recent_fruit_ids(
    session: Session,
    user_id: int,
    *,
    since: date,
    until: date | None = None,
    limit: int = 30,
) -> tuple[int, ...]:
    conditions = [
        Recommendation.user_id == user_id,
        Recommendation.recommendation_date >= since,
    ]
    if until is not None:
        conditions.append(Recommendation.recommendation_date <= until)
    statement = (
        select(RecommendationItem.fruit_id)
        .join(Recommendation)
        .where(*conditions)
        .order_by(
            Recommendation.recommendation_date.desc(),
            Recommendation.refresh_number.desc(),
            RecommendationItem.rank,
        )
        .limit(limit)
    )
    ordered = session.execute(statement).scalars()
    return tuple(dict.fromkeys(ordered))


def feedback_by_fruit(
    session: Session,
    user_id: int,
    *,
    since: datetime,
    until: datetime | None = None,
    limit: int = 100,
) -> dict[int, tuple[str, ...]]:
    conditions = [
        RecommendationFeedback.user_id == user_id,
        RecommendationFeedback.created_at >= since,
    ]
    if until is not None:
        conditions.append(RecommendationFeedback.created_at <= until)
    statement = (
        select(
            RecommendationItem.fruit_id,
            RecommendationFeedback.feedback_type,
        )
        .join(
            RecommendationItem,
            RecommendationItem.id
            == RecommendationFeedback.recommendation_item_id,
        )
        .where(*conditions)
        .order_by(RecommendationFeedback.created_at.desc())
        .limit(limit)
    )
    grouped: defaultdict[int, list[str]] = defaultdict(list)
    for fruit_id, feedback_type in session.execute(statement):
        grouped[fruit_id].append(feedback_type)
    return {
        fruit_id: tuple(feedback_types)
        for fruit_id, feedback_types in grouped.items()
    }


def history_events(
    session: Session,
    user_id: int,
    *,
    since: date,
    until: date | None = None,
    limit: int = 200,
) -> tuple[HistoryEvent, ...]:
    conditions = [
        Recommendation.user_id == user_id,
        Recommendation.recommendation_date >= since,
    ]
    if until is not None:
        conditions.append(Recommendation.recommendation_date <= until)
    statement = (
        select(
            Recommendation.recommendation_date,
            RecommendationItem.fruit_id,
            func.count(RecommendationItem.id),
        )
        .join(RecommendationItem, RecommendationItem.recommendation_id == Recommendation.id)
        .where(*conditions)
        .group_by(Recommendation.recommendation_date, RecommendationItem.fruit_id)
        .order_by(Recommendation.recommendation_date.desc())
        .limit(limit)
    )
    eaten_statement = (
        select(
            Recommendation.recommendation_date,
            RecommendationItem.fruit_id,
            func.count(RecommendationFeedback.id),
        )
        .join(RecommendationItem, RecommendationItem.recommendation_id == Recommendation.id)
        .join(RecommendationFeedback, RecommendationFeedback.recommendation_item_id == RecommendationItem.id)
        .where(
            *conditions,
            RecommendationFeedback.user_id == user_id,
            RecommendationFeedback.feedback_type == "eaten",
        )
        .group_by(Recommendation.recommendation_date, RecommendationItem.fruit_id)
    )
    eaten = {
        (occurred_on, fruit_id): int(count)
        for occurred_on, fruit_id, count in session.execute(eaten_statement)
    }
    return tuple(
        HistoryEvent(
            fruit_id=int(fruit_id),
            occurred_on=occurred_on,
            times_shown=int(times_shown),
            eaten_count=eaten.get((occurred_on, fruit_id), 0),
        )
        for occurred_on, fruit_id, times_shown in session.execute(statement)
    )


def feedback_events(
    session: Session,
    user_id: int,
    *,
    since: datetime,
    until: datetime | None = None,
    limit: int = 200,
) -> tuple[FeedbackEvent, ...]:
    conditions = [
        Recommendation.user_id == user_id,
        RecommendationFeedback.user_id == user_id,
        RecommendationFeedback.created_at >= since,
    ]
    if until is not None:
        conditions.append(RecommendationFeedback.created_at <= until)
    statement = (
        select(
            RecommendationItem.fruit_id,
            RecommendationFeedback.feedback_type,
            RecommendationFeedback.created_at,
        )
        .join(Recommendation, Recommendation.id == RecommendationItem.recommendation_id)
        .join(RecommendationFeedback, RecommendationFeedback.recommendation_item_id == RecommendationItem.id)
        .where(*conditions)
        .order_by(RecommendationFeedback.created_at.desc())
        .limit(limit)
    )
    return tuple(
        FeedbackEvent(
            fruit_id=int(fruit_id),
            feedback_type=feedback_type,
            occurred_at=created_at,
        )
        for fruit_id, feedback_type, created_at in session.execute(statement)
    )


def previous_pairs(
    session: Session,
    user_id: int,
    *,
    since: date,
    until: date | None = None,
    limit: int = 30,
) -> tuple[frozenset[int], ...]:
    recommendations = list_history(session, user_id, limit=limit)
    return tuple(
        frozenset(item.fruit_id for item in recommendation.items)
        for recommendation in recommendations
        if recommendation.recommendation_date >= since
        and (until is None or recommendation.recommendation_date <= until)
        and len(recommendation.items) >= 2
    )


def add_recommendation(
    session: Session,
    recommendation: Recommendation,
) -> Recommendation:
    session.add(recommendation)
    session.flush()
    return recommendation


def get_item(
    session: Session,
    item_id: int,
) -> RecommendationItem | None:
    statement = (
        select(RecommendationItem)
        .where(RecommendationItem.id == item_id)
        .options(
            joinedload(RecommendationItem.recommendation),
            selectinload(RecommendationItem.feedback),
        )
    )
    return session.execute(statement).scalar_one_or_none()


def get_feedback(
    session: Session,
    *,
    item_id: int,
    user_id: int,
    feedback_type: str,
) -> RecommendationFeedback | None:
    statement = select(RecommendationFeedback).where(
        RecommendationFeedback.recommendation_item_id == item_id,
        RecommendationFeedback.user_id == user_id,
        RecommendationFeedback.feedback_type == feedback_type,
    )
    return session.execute(statement).scalar_one_or_none()


def add_feedback(
    session: Session,
    feedback: RecommendationFeedback,
) -> RecommendationFeedback:
    session.add(feedback)
    session.flush()
    return feedback


__all__ = [
    "acquire_user_lock",
    "add_feedback",
    "add_recommendation",
    "feedback_by_fruit",
    "feedback_events",
    "get_active_recommendation",
    "get_feedback",
    "get_item",
    "get_recommendation",
    "list_history",
    "history_events",
    "next_refresh_number",
    "previous_pairs",
    "recent_fruit_ids",
]
