"""用户资料和水果偏好的业务服务。

Router 只负责 HTTP 参数和依赖注入；本模块负责创建、部分更新、偏好
合并、事务提交以及把 ORM 转成 Pydantic 响应。推荐算法不会从这里直接
读取数据库，而是由推荐 Application Service 单独编排。
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ResourceConflictError, ResourceNotFoundError
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
    """创建未绑定 Auth 的兼容入口；受保护 API 使用 principal 版本。"""

    user = User(**payload.model_dump())
    user_repository.add_user(session, user)
    session.commit()
    return UserRead.model_validate(user)


def create_user_for_principal(
    session: Session,
    payload: UserCreate,
    auth_user_id: UUID,
) -> UserRead:
    """把已验证 JWT 的 UUID 绑定到唯一 public.users 资料。"""

    if user_repository.get_user_by_auth_user_id(session, auth_user_id):
        raise ResourceConflictError("当前账号已经创建用户资料")
    user = User(auth_user_id=auth_user_id, **payload.model_dump())
    try:
        user_repository.add_user(session, user)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ResourceConflictError("当前账号已经创建用户资料") from error
    return UserRead.model_validate(user)


def get_user(session: Session, user_id: int) -> UserRead:
    """按已授权的业务用户 ID 读取资料，不负责确认调用者身份。"""

    user = _require_user(session, user_id)
    return UserRead.model_validate(user)


def update_user(
    session: Session,
    user_id: int,
    payload: UserUpdate,
) -> UserRead:
    """使用 ``exclude_unset`` 做字段级更新，并在成功后提交事务。"""

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
    """读取用户全部偏好，返回稳定的 fruit_id 顺序。"""

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
    """校验水果存在后合并偏好，不删除熟悉度或历史行。"""

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
                item.has_tried,
                item.willing_to_try,
                "has_tried" in item.model_fields_set,
                "willing_to_try" in item.model_fields_set,
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
    """把不存在的业务用户统一转换为 404 领域错误。"""

    user = user_repository.get_user(session, user_id)
    if user is None:
        raise ResourceNotFoundError("用户不存在")
    return user


__all__ = [
    "create_user",
    "create_user_for_principal",
    "get_fruit_preferences",
    "get_user",
    "replace_fruit_preferences",
    "update_user",
]
