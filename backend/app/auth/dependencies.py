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


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_principal(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError()
    return get_jwt_verifier().verify(credentials.credentials)


CurrentPrincipal = Annotated[AuthPrincipal, Depends(get_current_principal)]
DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_current_user(
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> User:
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
