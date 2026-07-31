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
    limit: int = 30,
) -> tuple[int, ...]:
    statement = (
        select(RecommendationItem.fruit_id)
        .join(Recommendation)
        .where(
            Recommendation.user_id == user_id,
            Recommendation.recommendation_date >= since,
        )
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
    limit: int = 100,
) -> dict[int, tuple[str, ...]]:
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
        .where(
            RecommendationFeedback.user_id == user_id,
            RecommendationFeedback.created_at >= since,
        )
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
    "get_active_recommendation",
    "get_feedback",
    "get_item",
    "get_recommendation",
    "list_history",
    "next_refresh_number",
    "recent_fruit_ids",
]
