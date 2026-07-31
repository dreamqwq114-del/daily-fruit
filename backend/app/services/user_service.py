from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.errors import ResourceNotFoundError
from app.models import User
from app.repositories import fruit_repository, user_repository
from app.schemas.user import (
    UserCreate,
    UserFruitPreferenceRead,
    UserFruitPreferencesUpdate,
    UserRead,
    UserUpdate,
)


def create_user(session: Session, payload: UserCreate) -> UserRead:
    user = User(**payload.model_dump())
    user_repository.add_user(session, user)
    session.commit()
    return UserRead.model_validate(user)


def get_user(session: Session, user_id: int) -> UserRead:
    user = _require_user(session, user_id)
    return UserRead.model_validate(user)


def update_user(
    session: Session,
    user_id: int,
    payload: UserUpdate,
) -> UserRead:
    user = _require_user(session, user_id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field_name, value)
    user.updated_at = datetime.now(UTC)
    session.commit()
    return UserRead.model_validate(user)


def get_fruit_preferences(
    session: Session,
    user_id: int,
) -> list[UserFruitPreferenceRead]:
    _require_user(session, user_id)
    return [
        UserFruitPreferenceRead.model_validate(item)
        for item in user_repository.list_preferences(session, user_id)
    ]


def replace_fruit_preferences(
    session: Session,
    user_id: int,
    payload: UserFruitPreferencesUpdate,
) -> list[UserFruitPreferenceRead]:
    _require_user(session, user_id)
    requested_ids = {item.fruit_id for item in payload.preferences}
    existing_ids = fruit_repository.existing_fruit_ids(
        session,
        requested_ids,
    )
    missing_ids = sorted(requested_ids - existing_ids)
    if missing_ids:
        raise ResourceNotFoundError(
            f"水果不存在：{', '.join(map(str, missing_ids))}"
        )

    preferences = user_repository.replace_preferences(
        session,
        user_id,
        (
            (
                item.fruit_id,
                item.preference_score,
                item.is_forbidden,
            )
            for item in payload.preferences
        ),
    )
    session.commit()
    return [
        UserFruitPreferenceRead.model_validate(item)
        for item in preferences
    ]


def _require_user(session: Session, user_id: int) -> User:
    user = user_repository.get_user(session, user_id)
    if user is None:
        raise ResourceNotFoundError("用户不存在")
    return user


__all__ = [
    "create_user",
    "get_fruit_preferences",
    "get_user",
    "replace_fruit_preferences",
    "update_user",
]
