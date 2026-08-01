"""集中读取并校验后端运行时、迁移、测试和 Supabase Auth 配置。

配置使用 Pydantic Settings 从 ``backend/.env`` 和进程环境读取。三种
数据库 URL 按用途隔离：runtime 给 FastAPI，migration 给 Alembic，test
只允许指向可丢弃的本地 ``daily_fruit_test`` 数据库。
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, unquote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
DATABASE_DRIVER = "postgresql+psycopg"
SECURE_SSL_MODES = {"require", "verify-ca", "verify-full"}
DatabasePurpose = Literal["runtime", "migration", "test"]


def _is_supabase_host(host: str) -> bool:
    """判断主机是否属于 Supabase，供测试库和 SSL 规则复用。"""

    return any(
        host == domain or host.endswith(f".{domain}")
        for domain in ("supabase.co", "supabase.com")
    )


def _validate_database_url(
    value: str,
    *,
    variable_name: str,
    purpose: DatabasePurpose,
) -> None:
    """检查 psycopg 驱动、数据库名、测试隔离和 Supabase SSL 约束。"""

    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"{variable_name} is not a valid database URL") from error

    if parsed.scheme != DATABASE_DRIVER or not host or not parsed.path.strip("/"):
        raise ValueError(
            f"{variable_name} must use postgresql+psycopg:// with a host "
            "and database name"
        )

    if purpose == "test":
        if _is_supabase_host(host):
            raise ValueError(
                "TEST_DATABASE_URL must not point to a Supabase project"
            )

        database_name = unquote(parsed.path.strip("/")).lower()
        if "daily_fruit_test" not in database_name:
            raise ValueError(
                "TEST_DATABASE_URL database name must contain daily_fruit_test"
            )
        return

    if _is_supabase_host(host):
        ssl_mode = parse_qs(parsed.query).get("sslmode", [""])[0].lower()
        if ssl_mode not in SECURE_SSL_MODES:
            raise ValueError(
                f"{variable_name} must enable SSL for Supabase connections"
            )
        if port == 6543:
            raise ValueError(
                f"{variable_name} must not use a transaction pooler on port 6543"
            )


class Settings(BaseSettings):
    """应用的类型化配置；字段 alias 对应 ``.env.example`` 的变量名。"""

    database_url: str | None = Field(
        default=None,
        alias="DATABASE_URL",
        repr=False,
    )
    migration_database_url: str | None = Field(
        default=None,
        alias="MIGRATION_DATABASE_URL",
        repr=False,
    )
    test_database_url: str | None = Field(
        default=None,
        alias="TEST_DATABASE_URL",
        repr=False,
    )
    supabase_url: str | None = Field(
        default=None,
        alias="SUPABASE_URL",
    )
    supabase_jwt_audience: str = Field(
        default="authenticated",
        min_length=1,
        max_length=100,
        alias="SUPABASE_JWT_AUDIENCE",
    )
    database_connect_timeout_seconds: int = Field(
        default=5,
        ge=1,
        le=30,
        alias="DATABASE_CONNECT_TIMEOUT_SECONDS",
    )
    database_pool_size: int = Field(
        default=5,
        ge=1,
        le=20,
        alias="DATABASE_POOL_SIZE",
    )
    database_max_overflow: int = Field(
        default=5,
        ge=0,
        le=20,
        alias="DATABASE_MAX_OVERFLOW",
    )
    frontend_origin: str = Field(
        default="http://localhost:5173",
        alias="FRONTEND_ORIGIN",
    )
    app_timezone: str = Field(
        default="Asia/Shanghai",
        alias="APP_TIMEZONE",
    )
    app_env: Literal["development", "test", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    debug: bool = Field(default=True, alias="DEBUG")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    @field_validator(
        "database_url",
        "migration_database_url",
        "test_database_url",
        "supabase_url",
        mode="before",
    )
    @classmethod
    def normalize_optional_database_url(cls, value: object) -> object:
        """把空字符串当作未配置，避免空 URL 绕过可选数据库逻辑。"""

        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("app_timezone")
    @classmethod
    def validate_app_timezone(cls, value: str) -> str:
        """确保日期计算使用真实 IANA 时区，而不是拼写错误的字符串。"""

        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("APP_TIMEZONE must be a valid IANA timezone") from error
        return value

    @model_validator(mode="after")
    def validate_environment_and_database_urls(self) -> "Settings":
        """执行 production/debug、数据库 URL 和 Supabase URL 的组合校验。"""

        if self.app_env == "production" and self.debug:
            raise ValueError("DEBUG must be false when APP_ENV=production")

        urls: tuple[
            tuple[str, str | None, DatabasePurpose],
            ...,
        ] = (
            ("DATABASE_URL", self.database_url, "runtime"),
            (
                "MIGRATION_DATABASE_URL",
                self.migration_database_url,
                "migration",
            ),
            ("TEST_DATABASE_URL", self.test_database_url, "test"),
        )
        for variable_name, value, purpose in urls:
            if value is not None:
                _validate_database_url(
                    value,
                    variable_name=variable_name,
                    purpose=purpose,
                )

        if self.supabase_url is not None:
            parsed_supabase_url = urlsplit(self.supabase_url)
            host = (parsed_supabase_url.hostname or "").lower()
            is_local = host in {"127.0.0.1", "localhost"}
            allowed_schemes = {"http", "https"} if is_local else {"https"}
            if (
                parsed_supabase_url.username is not None
                or parsed_supabase_url.password is not None
                or parsed_supabase_url.query
                or parsed_supabase_url.fragment
                or parsed_supabase_url.path not in {"", "/"}
                or parsed_supabase_url.scheme not in allowed_schemes
                or not host
            ):
                raise ValueError(
                    "SUPABASE_URL must be an HTTPS project origin without "
                    "credentials, query parameters, fragments, or paths"
                )
            self.supabase_url = self.supabase_url.rstrip("/")

        return self

    @property
    def supabase_jwt_issuer(self) -> str | None:
        if self.supabase_url is None:
            return None
        return f"{self.supabase_url}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str | None:
        if self.supabase_jwt_issuer is None:
            return None
        return f"{self.supabase_jwt_issuer}/.well-known/jwks.json"

    def database_url_for(self, purpose: DatabasePurpose) -> str | None:
        """按明确用途返回连接串；不允许调用方隐式复用测试或迁移连接。"""

        if purpose == "runtime":
            return self.database_url
        if purpose == "migration":
            return self.migration_database_url
        if purpose == "test":
            return self.test_database_url
        raise ValueError("Unsupported database purpose")


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，使整个进程使用同一份已校验设置。"""

    return Settings()
