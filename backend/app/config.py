from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, unquote, urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
DATABASE_DRIVER = "postgresql+psycopg"
SECURE_SSL_MODES = {"require", "verify-ca", "verify-full"}
DatabasePurpose = Literal["runtime", "migration", "test"]


def _is_supabase_host(host: str) -> bool:
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
        mode="before",
    )
    @classmethod
    def normalize_optional_database_url(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_environment_and_database_urls(self) -> "Settings":
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

        return self

    def database_url_for(self, purpose: DatabasePurpose) -> str | None:
        if purpose == "runtime":
            return self.database_url
        if purpose == "migration":
            return self.migration_database_url
        if purpose == "test":
            return self.test_database_url
        raise ValueError("Unsupported database purpose")


@lru_cache
def get_settings() -> Settings:
    return Settings()
