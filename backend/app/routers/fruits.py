from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_principal
from app.database import get_database_session
from app.schemas.fruit import FruitDetail, FruitRead
from app.services import fruit_service


router = APIRouter(
    prefix="/api/fruits",
    tags=["fruits"],
    dependencies=[Depends(get_current_principal)],
)
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get("", response_model=list[FruitRead])
def list_fruits(session: DatabaseSession) -> list[FruitRead]:
    return fruit_service.list_fruits(session)


@router.get("/{fruit_id}", response_model=FruitDetail)
def get_fruit(fruit_id: int, session: DatabaseSession) -> FruitDetail:
    return fruit_service.get_fruit(session, fruit_id)


__all__ = ["router"]
