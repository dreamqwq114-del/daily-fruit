"""FastAPI 依赖：把 Bearer token 解析成当前认证用户。

路由只声明 ``CurrentPrincipal`` 或 ``CurrentUser``，就能复用同一套
认证、数据库会话和资源不存在处理逻辑，避免每个路由重复实现授权。
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt_verifier import get_jwt_verifier
from app.auth.principal import AuthPrincipal
from app.database import get_database_session
from app.errors import AuthenticationError, ResourceNotFoundError
from app.models import User
from app.repositories import user_repository


# ``auto_error=False`` 让我们统一返回项目自己的 401 响应，而不是让
# FastAPI 在不同缺失头部的情况下生成不一致的错误正文。
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_principal(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthPrincipal:
    """要求 Bearer 认证，并交给 JwtVerifier 校验签名和声明。"""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError()
    return get_jwt_verifier().verify(credentials.credentials)


CurrentPrincipal = Annotated[AuthPrincipal, Depends(get_current_principal)]
DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_current_user(
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> User:
    """用已验证 JWT 的 ``sub`` 查找 public.users，禁止信任客户端 user_id。"""

    user = user_repository.get_user_by_auth_user_id(
        session,
        principal.auth_user_id,
    )
    if user is None:
        raise ResourceNotFoundError("尚未创建用户资料")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


__all__ = [
    "CurrentPrincipal",
    "CurrentUser",
    "get_current_principal",
    "get_current_user",
]
