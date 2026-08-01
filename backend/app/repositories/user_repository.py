"""用户 ORM 查询与偏好持久化。

Repository 只操作 SQLAlchemy Session，不处理 HTTP、JWT 或推荐评分。偏好
更新采用 merge：页面管理的 score/forbidden 可以清空，但 has_tried 和
willing_to_try 只有在请求显式提供时才覆盖。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import User, UserFruitPreference


def get_user(
    session: Session,
    user_id: int,
    *,
    include_preferences: bool = False,
) -> User | None:
    """按 public.users 主键查询，可选预加载偏好避免 N+1。"""

    statement = select(User).where(User.id == user_id)
    if include_preferences:
        statement = statement.options(selectinload(User.fruit_preferences))
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
        statement = statement.options(selectinload(User.fruit_preferences))
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

    设置页面负责 ``preference_score`` 和 ``is_forbidden``；熟悉度字段只有
    旧客户端明确提交时才修改。保留空偏好行可以避免用户清空设置后丢失
    将来算法可能使用的熟悉度信号。
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
            item = UserFruitPreference(
                user_id=user_id,
                fruit_id=fruit_id,
                preference_score=preference_score,
                is_forbidden=is_forbidden,
                has_tried=(
                    True
                    if preference_score == 2 and not has_tried_provided
                    else has_tried
                ),
                willing_to_try=(
                    willing_to_try if willing_to_try_provided else None
                ),
            )
            session.add(item)
        else:
            item.preference_score = preference_score
            item.is_forbidden = is_forbidden
            if has_tried_provided and preference_score != 2:
                item.has_tried = has_tried
            if willing_to_try_provided:
                item.willing_to_try = willing_to_try
            item.updated_at = now

    for fruit_id, item in existing.items():
        if fruit_id not in submitted_ids:
            item.preference_score = None
            item.is_forbidden = False
            item.updated_at = now

    session.flush()
    return list_preferences(session, user_id)


__all__ = [
    "add_user",
    "get_user",
    "get_user_by_auth_user_id",
    "list_preferences",
    "replace_preferences",
]
