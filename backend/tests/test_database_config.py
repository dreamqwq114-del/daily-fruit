import pytest
from pydantic import ValidationError
from sqlalchemy.pool import NullPool

from app import database
from app.config import Settings


LOCAL_RUNTIME_URL = (
    "postgresql+psycopg://fruit:password@localhost:5432/daily_fruit"
)
LOCAL_MIGRATION_URL = (
    "postgresql+psycopg://fruit_admin:password@localhost:5432/daily_fruit"
)
LOCAL_TEST_URL = (
    "postgresql+psycopg://fruit_test:password@localhost:5432/"
    "daily_fruit_test"
)


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "DATABASE_URL": None,
        "MIGRATION_DATABASE_URL": None,
        "TEST_DATABASE_URL": None,
        "DATABASE_CONNECT_TIMEOUT_SECONDS": 5,
        "DATABASE_POOL_SIZE": 5,
        "DATABASE_MAX_OVERFLOW": 5,
        "FRONTEND_ORIGIN": "http://localhost:5173",
        "APP_ENV": "development",
        "DEBUG": True,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_empty_database_urls_are_treated_as_unconfigured() -> None:
    settings = make_settings(
        DATABASE_URL="",
        MIGRATION_DATABASE_URL="  ",
        TEST_DATABASE_URL="",
    )

    assert settings.database_url_for("runtime") is None
    assert settings.database_url_for("migration") is None
    assert settings.database_url_for("test") is None


def test_database_urls_are_resolved_by_purpose() -> None:
    settings = make_settings(
        DATABASE_URL=LOCAL_RUNTIME_URL,
        MIGRATION_DATABASE_URL=LOCAL_MIGRATION_URL,
        TEST_DATABASE_URL=LOCAL_TEST_URL,
    )

    assert settings.database_url_for("runtime") == LOCAL_RUNTIME_URL
    assert settings.database_url_for("migration") == LOCAL_MIGRATION_URL
    assert settings.database_url_for("test") == LOCAL_TEST_URL


def test_database_url_purposes_do_not_fall_back_to_runtime() -> None:
    settings = make_settings(DATABASE_URL=LOCAL_RUNTIME_URL)

    assert settings.database_url_for("runtime") == LOCAL_RUNTIME_URL
    assert settings.database_url_for("migration") is None
    assert settings.database_url_for("test") is None


def test_production_rejects_debug_without_exposing_database_password() -> None:
    secret = "do-not-display-this-password"

    with pytest.raises(ValidationError) as error:
        make_settings(
            DATABASE_URL=(
                "postgresql+psycopg://fruit:"
                f"{secret}@localhost:5432/daily_fruit"
            ),
            APP_ENV="production",
            DEBUG=True,
        )

    assert "DEBUG must be false" in str(error.value)
    assert secret not in str(error.value)


@pytest.mark.parametrize(
    "test_url",
    [
        (
            "postgresql+psycopg://postgres:password@"
            "db.example.supabase.co:5432/postgres?sslmode=require"
        ),
        (
            "postgresql+psycopg://postgres.example:password@"
            "aws-0-region.pooler.supabase.com:5432/postgres"
            "?sslmode=require"
        ),
    ],
)
def test_test_database_url_rejects_supabase_hosts(test_url: str) -> None:
    with pytest.raises(
        ValidationError,
        match="must not point to a Supabase project",
    ):
        make_settings(TEST_DATABASE_URL=test_url)


def test_test_database_url_requires_disposable_database_name() -> None:
    with pytest.raises(
        ValidationError,
        match="database name must contain daily_fruit_test",
    ):
        make_settings(
            TEST_DATABASE_URL=(
                "postgresql+psycopg://fruit:password@localhost:5432/postgres"
            )
        )


@pytest.mark.parametrize(
    "variable_name",
    ["DATABASE_URL", "MIGRATION_DATABASE_URL"],
)
def test_supabase_connections_require_ssl(variable_name: str) -> None:
    with pytest.raises(ValidationError, match="must enable SSL"):
        make_settings(
            **{
                variable_name: (
                    "postgresql+psycopg://postgres:password@"
                    "db.example.supabase.co:5432/postgres"
                )
            }
        )


@pytest.mark.parametrize(
    "variable_name",
    ["DATABASE_URL", "MIGRATION_DATABASE_URL"],
)
def test_transaction_pooler_is_rejected(variable_name: str) -> None:
    with pytest.raises(
        ValidationError,
        match="must not use a transaction pooler",
    ):
        make_settings(
            **{
                variable_name: (
                    "postgresql+psycopg://postgres.example:password@"
                    "aws-0-region.pooler.supabase.com:6543/postgres"
                    "?sslmode=require"
                )
            }
        )


def test_supabase_session_pooler_with_ssl_is_accepted() -> None:
    session_pooler_url = (
        "postgresql+psycopg://postgres.example:password@"
        "aws-0-region.pooler.supabase.com:5432/postgres"
        "?sslmode=require"
    )

    settings = make_settings(DATABASE_URL=session_pooler_url)

    assert settings.database_url_for("runtime") == session_pooler_url


def test_database_url_requires_psycopg_driver() -> None:
    with pytest.raises(
        ValidationError,
        match=r"must use postgresql\+psycopg",
    ):
        make_settings(
            DATABASE_URL=(
                "postgresql://fruit:password@localhost:5432/daily_fruit"
            )
        )


def test_engine_factory_uses_separate_pooling_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    sentinel = object()

    def fake_create_engine(
        url: str,
        **options: object,
    ) -> object:
        calls.append((url, options))
        return sentinel

    monkeypatch.setattr(database, "create_engine", fake_create_engine)
    settings = make_settings(
        DATABASE_URL=LOCAL_RUNTIME_URL,
        MIGRATION_DATABASE_URL=LOCAL_MIGRATION_URL,
        TEST_DATABASE_URL=LOCAL_TEST_URL,
        DATABASE_CONNECT_TIMEOUT_SECONDS=7,
        DATABASE_POOL_SIZE=4,
        DATABASE_MAX_OVERFLOW=2,
    )

    runtime_engine = database.create_database_engine(settings=settings)
    migration_engine = database.create_database_engine(
        "migration",
        settings=settings,
    )
    test_engine = database.create_database_engine("test", settings=settings)

    assert runtime_engine is sentinel
    assert migration_engine is sentinel
    assert test_engine is sentinel
    assert calls[0] == (
        LOCAL_RUNTIME_URL,
        {
            "connect_args": {"connect_timeout": 7},
            "pool_pre_ping": True,
            "pool_size": 4,
            "max_overflow": 2,
        },
    )
    assert calls[1][0] == LOCAL_MIGRATION_URL
    assert calls[1][1]["poolclass"] is NullPool
    assert calls[2][0] == LOCAL_TEST_URL
    assert calls[2][1]["poolclass"] is NullPool
