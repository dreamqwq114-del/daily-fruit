from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import User, UserFruitPreference


def get_user(
    session: Session,
    user_id: int,
    *,
    include_preferences: bool = False,
) -> User | None:
    statement = select(User).where(User.id == user_id)
    if include_preferences:
        statement = statement.options(selectinload(User.fruit_preferences))
    return session.execute(statement).scalar_one_or_none()


def add_user(session: Session, user: User) -> User:
    session.add(user)
    session.flush()
    return user


def list_preferences(
    session: Session,
    user_id: int,
) -> list[UserFruitPreference]:
    statement = (
        select(UserFruitPreference)
        .where(UserFruitPreference.user_id == user_id)
        .order_by(UserFruitPreference.fruit_id)
    )
    return list(session.execute(statement).scalars())


def replace_preferences(
    session: Session,
    user_id: int,
    preferences: Iterable[tuple[int, object, bool]],
) -> list[UserFruitPreference]:
    existing = {
        item.fruit_id: item
        for item in list_preferences(session, user_id)
    }
    submitted_ids: set[int] = set()
    now = datetime.now(UTC)
    for fruit_id, preference_score, is_forbidden in preferences:
        submitted_ids.add(fruit_id)
        item = existing.get(fruit_id)
        if item is None:
            item = UserFruitPreference(
                user_id=user_id,
                fruit_id=fruit_id,
                preference_score=preference_score,
                is_forbidden=is_forbidden,
            )
            session.add(item)
        else:
            item.preference_score = preference_score
            item.is_forbidden = is_forbidden
            item.updated_at = now

    for fruit_id, item in existing.items():
        if fruit_id not in submitted_ids:
            session.delete(item)

    session.flush()
    return list_preferences(session, user_id)


__all__ = [
    "add_user",
    "get_user",
    "list_preferences",
    "replace_preferences",
]
