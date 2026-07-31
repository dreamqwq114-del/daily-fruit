from sqlalchemy.orm import Session

from app.errors import ResourceNotFoundError
from app.repositories import fruit_repository
from app.schemas.fruit import FruitDetail, FruitRead


def list_fruits(session: Session) -> list[FruitRead]:
    return [
        FruitRead.model_validate(fruit)
        for fruit in fruit_repository.list_active_fruits(session)
    ]


def get_fruit(session: Session, fruit_id: int) -> FruitDetail:
    fruit = fruit_repository.get_active_fruit(session, fruit_id)
    if fruit is None:
        raise ResourceNotFoundError("水果不存在或已停用")
    return FruitDetail.model_validate(fruit)


__all__ = ["get_fruit", "list_fruits"]
