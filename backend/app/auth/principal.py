"""认证主体的数据合同，不包含业务权限或数据库模型。"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    """JWT 通过验证后，业务层可以安全使用的身份标识。"""

    auth_user_id: UUID
    session_id: UUID


__all__ = ["AuthPrincipal"]
