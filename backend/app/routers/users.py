from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.schemas.user import (
    UserCreate,
    UserFruitPreferenceRead,
    UserFruitPreferencesUpdate,
    UserRead,
    UserUpdate,
)
from app.services import user_service


router = APIRouter(prefix="/api/users", tags=["users"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    session: DatabaseSession,
) -> UserRead:
    return user_service.create_user(session, payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, session: DatabaseSession) -> UserRead:
    return user_service.get_user(session, user_id)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    session: DatabaseSession,
) -> UserRead:
    return user_service.update_user(session, user_id, payload)


@router.get(
    "/{user_id}/fruit-preferences",
    response_model=list[UserFruitPreferenceRead],
)
def get_fruit_preferences(
    user_id: int,
    session: DatabaseSession,
) -> list[UserFruitPreferenceRead]:
    return user_service.get_fruit_preferences(session, user_id)


@router.put(
    "/{user_id}/fruit-preferences",
    response_model=list[UserFruitPreferenceRead],
)
def replace_fruit_preferences(
    user_id: int,
    payload: UserFruitPreferencesUpdate,
    session: DatabaseSession,
) -> list[UserFruitPreferenceRead]:
    return user_service.replace_fruit_preferences(
        session,
        user_id,
        payload,
    )


__all__ = ["router"]
