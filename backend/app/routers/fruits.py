"""受保护的水果目录只读接口。"""

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
# 目录数据不直接暴露给匿名浏览器；CurrentPrincipal 只做 token 验证。
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get("", response_model=list[FruitRead])
def list_fruits(session: DatabaseSession) -> list[FruitRead]:
    """返回 active 水果目录，供建档和偏好页面展示。"""

    return fruit_service.list_fruits(session)


@router.get("/{fruit_id}", response_model=FruitDetail)
def get_fruit(fruit_id: int, session: DatabaseSession) -> FruitDetail:
    """按 ID 返回一个 active 水果及营养/季节详情。"""

    return fruit_service.get_fruit(session, fruit_id)


__all__ = ["router"]
