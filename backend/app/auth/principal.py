from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    auth_user_id: UUID
    session_id: UUID


__all__ = ["AuthPrincipal"]
