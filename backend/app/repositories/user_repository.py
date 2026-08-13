"""用户 ORM 查询与偏好持久化。

Repository 只操作 SQLAlchemy Session，不处理 HTTP、JWT 或推荐评分。偏好
更新采用 merge：页面管理的 score/forbidden 可以清空。熟悉度通常只在
显式提供时覆盖，但特别喜欢会推导 has_tried=true，不适用的尝试意愿会
被清为 null。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    User,
    UserFruitOptionPreference,
    UserFruitPreference,
)


def get_user(
    session: Session,
    user_id: int,
    *,
    include_preferences: bool = False,
) -> User | None:
    """按 public.users 主键查询，可选预加载偏好避免 N+1。"""

    statement = select(User).where(User.id == user_id)
    if include_preferences:
        statement = statement.options(
            selectinload(User.fruit_preferences),
            selectinload(User.fruit_option_preferences),
        )
    return session.execute(statement).scalar_one_or_none()


def get_user_by_auth_user_id(
    session: Session,
    auth_user_id: UUID,
    *,
    include_preferences: bool = False,
) -> User | None:
    """按 Supabase Auth UUID 查询业务用户绑定关系。"""

    statement = select(User).where(User.auth_user_id == auth_user_id)
    if include_preferences:
        statement = statement.options(
            selectinload(User.fruit_preferences),
            selectinload(User.fruit_option_preferences),
        )
    return session.execute(statement).scalar_one_or_none()


def add_user(session: Session, user: User) -> User:
    """加入 Session 并 flush，令调用方立即获得数据库生成的 ID。"""

    session.add(user)
    session.flush()
    return user


def list_preferences(
    session: Session,
    user_id: int,
) -> list[UserFruitPreference]:
    """按 fruit_id 稳定读取一个用户的偏好行。"""

    statement = (
        select(UserFruitPreference)
        .where(UserFruitPreference.user_id == user_id)
        .order_by(UserFruitPreference.fruit_id)
    )
    return list(session.execute(statement).scalars())


def replace_preferences(
    session: Session,
    user_id: int,
    preferences: Iterable[
        tuple[
            int,
            object,
            bool,
            bool | None,
            bool | None,
            bool,
            bool,
        ]
    ],
) -> list[UserFruitPreference]:
    """合并页面管理字段，同时保留熟悉度数据。

    设置页面负责 ``preference_score`` 和 ``is_forbidden``。除两项状态机
    规则外，熟悉度字段只在旧客户端明确提交时修改：特别喜欢会推导
    ``has_tried=True``；最终状态不是明确没吃过时会清除无意义的
    ``willing_to_try``。保留空偏好行可以避免清空设置后丢失合法熟悉度。
    """
    existing = {
        item.fruit_id: item
        for item in list_preferences(session, user_id)
    }
    submitted_ids: set[int] = set()
    now = datetime.now(UTC)
    for (
        fruit_id,
        preference_score,
        is_forbidden,
        has_tried,
        willing_to_try,
        has_tried_provided,
        willing_to_try_provided,
    ) in preferences:
        submitted_ids.add(fruit_id)
        item = existing.get(fruit_id)
        if item is None:
            final_has_tried = (
                True
                if preference_score == 2
                else has_tried if has_tried_provided else None
            )
            item = UserFruitPreference(
                user_id=user_id,
                fruit_id=fruit_id,
                preference_score=preference_score,
                is_forbidden=is_forbidden,
                has_tried=final_has_tried,
                willing_to_try=(
                    willing_to_try
                    if final_has_tried is False and willing_to_try_provided
                    else None
                ),
            )
            session.add(item)
        else:
            item.preference_score = preference_score
            item.is_forbidden = is_forbidden
            if preference_score == 2:
                item.has_tried = True
            elif has_tried_provided:
                item.has_tried = has_tried
            if item.has_tried is not False:
                item.willing_to_try = None
            elif willing_to_try_provided:
                item.willing_to_try = willing_to_try
            item.updated_at = now

    for fruit_id, item in existing.items():
        if fruit_id not in submitted_ids:
            item.preference_score = None
            item.is_forbidden = False
            item.updated_at = now

    session.flush()
    return list_preferences(session, user_id)


def list_option_preferences(
    session: Session,
    user_id: int,
) -> list[UserFruitOptionPreference]:
    """按父水果、选项稳定读取当前用户的类型偏好。"""

    statement = (
        select(UserFruitOptionPreference)
        .where(UserFruitOptionPreference.user_id == user_id)
        .order_by(
            UserFruitOptionPreference.fruit_id,
            UserFruitOptionPreference.option_id,
        )
    )
    return list(session.execute(statement).scalars())


def replace_option_preferences(
    session: Session,
    user_id: int,
    preferences: Iterable[tuple[int, int, str | None]],
) -> list[UserFruitOptionPreference]:
    """以幂等替换方式保存类型偏好；``None`` 会删除该记录。"""

    existing = {
        item.option_id: item
        for item in list_option_preferences(session, user_id)
    }
    submitted: set[int] = set()
    now = datetime.now(UTC)
    for fruit_id, option_id, preference in preferences:
        submitted.add(option_id)
        item = existing.get(option_id)
        if preference is None:
            if item is not None:
                session.delete(item)
            continue
        if item is None:
            session.add(
                UserFruitOptionPreference(
                    user_id=user_id,
                    fruit_id=fruit_id,
                    option_id=option_id,
                    preference=preference,
                )
            )
        else:
            item.fruit_id = fruit_id
            item.preference = preference
            item.updated_at = now

    # An explicitly supplied replacement list is authoritative.  Clearing the
    # list therefore removes old rows, while an omitted field leaves them.
    for option_id, item in existing.items():
        if option_id not in submitted:
            session.delete(item)

    session.flush()
    return list_option_preferences(session, user_id)


__all__ = [
    "add_user",
    "get_user",
    "get_user_by_auth_user_id",
    "list_preferences",
    "list_option_preferences",
    "replace_preferences",
    "replace_option_preferences",
]
