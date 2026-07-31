from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Fruit


FRUIT_DETAIL_OPTIONS = (
    selectinload(Fruit.nutrition),
    selectinload(Fruit.seasons),
)


def list_active_fruits(session: Session) -> list[Fruit]:
    statement = (
        select(Fruit)
        .where(Fruit.is_active.is_(True))
        .options(*FRUIT_DETAIL_OPTIONS)
        .order_by(Fruit.id)
    )
    return list(session.execute(statement).scalars())


def get_active_fruit(session: Session, fruit_id: int) -> Fruit | None:
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
    if not fruit_ids:
        return set()
    statement = select(Fruit.id).where(Fruit.id.in_(fruit_ids))
    return set(session.execute(statement).scalars())


__all__ = [
    "existing_fruit_ids",
    "get_active_fruit",
    "list_active_fruits",
]
