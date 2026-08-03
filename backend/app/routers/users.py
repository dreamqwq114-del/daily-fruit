"""当前登录用户的资料和水果偏好 HTTP 路由。

路径统一使用 ``/api/me``，用户身份来自 ``CurrentUser``/``CurrentPrincipal``
依赖，而不是请求体或查询参数中的 user_id，因此浏览器不能选择别人的资料。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import CurrentPrincipal, CurrentUser
from app.database import get_database_session
from app.schemas.user import (
    UserCreate,
    UserFruitPreferenceRead,
    UserFruitOptionPreferenceRead,
    UserFruitPreferencesUpdate,
    UserRead,
    UserUpdate,
)
from app.services import user_service


router = APIRouter(prefix="/api/me", tags=["users"])
# Session 依赖只负责连接生命周期；业务提交和回滚由 service 控制。
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_current_user(
    payload: UserCreate,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> UserRead:
    """为当前已认证 Auth 用户创建一次性业务资料。"""

    return user_service.create_user_for_principal(
        session,
        payload,
        principal.auth_user_id,
    )


@router.get("", response_model=UserRead)
def get_current_user_profile(current_user: CurrentUser) -> UserRead:
    """返回当前 JWT 对应的资料，不接受外部 user_id。"""

    return UserRead.model_validate(current_user)


@router.put("", response_model=UserRead)
def update_current_user(
    payload: UserUpdate,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> UserRead:
    """部分更新当前用户的资料字段。"""

    return user_service.update_user(session, current_user.id, payload)


@router.get(
    "/fruit-preferences",
    response_model=list[UserFruitPreferenceRead],
)
def get_current_user_fruit_preferences(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[UserFruitPreferenceRead]:
    """读取当前用户的水果偏好。"""

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
    """合并当前用户提交的喜欢、不喜欢和禁止水果。"""

    return user_service.replace_fruit_preferences(
        session,
        current_user.id,
        payload,
    )


@router.get(
    "/fruit-option-preferences",
    response_model=list[UserFruitOptionPreferenceRead],
)
def get_current_user_fruit_option_preferences(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[UserFruitOptionPreferenceRead]:
    """读取当前用户明确保存的消费类型偏好。"""

    return user_service.get_fruit_option_preferences(session, current_user.id)


__all__ = ["router"]
