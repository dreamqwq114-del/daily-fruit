from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import CurrentPrincipal, CurrentUser
from app.database import get_database_session
from app.schemas.user import (
    UserCreate,
    UserFruitPreferenceRead,
    UserFruitPreferencesUpdate,
    UserRead,
    UserUpdate,
)
from app.services import user_service


router = APIRouter(prefix="/api/me", tags=["users"])
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_current_user(
    payload: UserCreate,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> UserRead:
    return user_service.create_user_for_principal(
        session,
        payload,
        principal.auth_user_id,
    )


@router.get("", response_model=UserRead)
def get_current_user_profile(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.put("", response_model=UserRead)
def update_current_user(
    payload: UserUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> UserRead:
    return user_service.update_user(session, current_user.id, payload)


@router.get(
    "/fruit-preferences",
    response_model=list[UserFruitPreferenceRead],
)
def get_current_user_fruit_preferences(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[UserFruitPreferenceRead]:
    return user_service.get_fruit_preferences(session, current_user.id)


@router.put(
    "/fruit-preferences",
    response_model=list[UserFruitPreferenceRead],
)
def replace_current_user_fruit_preferences(
    payload: UserFruitPreferencesUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[UserFruitPreferenceRead]:
    return user_service.replace_fruit_preferences(
        session,
        current_user.id,
        payload,
    )


__all__ = ["router"]
