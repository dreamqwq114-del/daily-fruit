"""水果目录查询，负责预加载推荐所需营养和季节关系。"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Fruit


FRUIT_DETAIL_OPTIONS = (
    # selectinload 将关系批量读取，避免推荐计算中逐水果 N+1 查询。
    selectinload(Fruit.nutrition),
    selectinload(Fruit.seasons),
)


def list_active_fruits(session: Session) -> list[Fruit]:
    """只返回 is_active 水果，并预加载算法所需详情。"""
    statement = (
        select(Fruit)
        .where(Fruit.is_active.is_(True))
        .options(*FRUIT_DETAIL_OPTIONS)
        .order_by(Fruit.id)
    )
    return list(session.execute(statement).scalars())


def get_active_fruit(session: Session, fruit_id: int) -> Fruit | None:
    """读取一个仍可推荐的水果及其详情。"""
    statement = (
        select(Fruit)
        .where(Fruit.id == fruit_id, Fruit.is_active.is_(True))
        .options(*FRUIT_DETAIL_OPTIONS)
    )
    return session.execute(statement).scalar_one_or_none()


def existing_fruit_ids(
    session: Session,
    fruit_ids: set[int],
) -> set[int]:
    """批量验证偏好请求中的水果 ID 是否存在。"""

    if not fruit_ids:
        return set()
    statement = select(Fruit.id).where(Fruit.id.in_(fruit_ids))
    return set(session.execute(statement).scalars())


__all__ = [
    "existing_fruit_ids",
    "get_active_fruit",
    "list_active_fruits",
]
