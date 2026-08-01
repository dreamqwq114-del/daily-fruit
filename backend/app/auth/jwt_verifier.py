"""验证 Supabase Auth access token，并转换为后端自己的认证主体。

请求链路是：HTTP ``Authorization: Bearer`` 头 → JWKS 公钥验证 →
issuer/audience/声明校验 → :class:`AuthPrincipal`。本模块不查询业务表，
也不把 token 内容写入日志；用户资料绑定由 ``dependencies.py`` 完成。
"""

from functools import lru_cache
from typing import Any, Protocol
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from app.auth.principal import AuthPrincipal
from app.config import Settings, get_settings
from app.errors import AuthenticationError, AuthenticationUnavailableError


ALLOWED_JWT_ALGORITHMS = frozenset({"RS256", "ES256"})


class SigningKeyClient(Protocol):
    """PyJWT JWKS 客户端的最小接口，便于单元测试注入假实现。"""

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class JwtVerifier:
    """只接受符合 Supabase JWT 合同的已签名 token。"""

    def __init__(
        self,
        settings: Settings,
        *,
        signing_key_client: SigningKeyClient | None = None,
    ) -> None:
        """根据公开的 Supabase 项目 URL 创建 JWKS 验证器。

        ``PyJWKClient`` 会按 JWKS URL 获取签名公钥；真实数据库密码和
        service role key 不会经过这里。缺少 Auth 配置时使用 503，避免把
        “认证服务未配置”和“用户 token 无效”混成同一个错误。
        """
        issuer = settings.supabase_jwt_issuer
        jwks_url = settings.supabase_jwks_url
        if issuer is None or jwks_url is None:
            raise AuthenticationUnavailableError()
        self._issuer = issuer
        self._audience = settings.supabase_jwt_audience
        self._signing_key_client = signing_key_client or PyJWKClient(
            jwks_url,
            cache_keys=True,
            cache_jwk_set=True,
            lifespan=300,
            timeout=5,
        )

    def verify(self, token: str) -> AuthPrincipal:
        """验证 token 并返回 UUID 主体；任何不可信输入都转换为安全错误。"""
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm not in ALLOWED_JWT_ALGORITHMS:
                raise AuthenticationError()
            signing_key = self._signing_key_client.get_signing_key_from_jwt(
                token
            )
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                options={
                    "require": [
                        "aud",
                        "exp",
                        "iat",
                        "iss",
                        "role",
                        "session_id",
                        "sub",
                    ]
                },
            )
            if claims.get("role") != "authenticated":
                raise AuthenticationError()
            if claims.get("is_anonymous") is True:
                raise AuthenticationError()
            return AuthPrincipal(
                auth_user_id=UUID(str(claims["sub"])),
                session_id=UUID(str(claims["session_id"])),
            )
        except AuthenticationError:
            raise
        except (PyJWTError, ValueError, KeyError, TypeError) as error:
            raise AuthenticationError() from error
        except Exception as error:
            raise AuthenticationUnavailableError() from error


@lru_cache
def get_jwt_verifier() -> JwtVerifier:
    """缓存进程级验证器，避免每个请求重复创建 JWKS 客户端。"""

    return JwtVerifier(get_settings())


__all__ = [
    "ALLOWED_JWT_ALGORITHMS",
    "JwtVerifier",
    "get_jwt_verifier",
]
