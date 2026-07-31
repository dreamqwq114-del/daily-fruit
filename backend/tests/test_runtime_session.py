from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import OperationalError

from app.clock import current_app_date
from app.config import Settings
from app import database
from app.errors import DatabaseUnavailableError, register_exception_handlers


class FakeSession:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def clear_runtime_caches() -> None:
    database.get_runtime_session_factory.cache_clear()
    database.get_runtime_engine.cache_clear()


def test_runtime_engine_is_reused(monkeypatch) -> None:
    sentinel = object()
    calls = 0

    def create_engine(_purpose: str):
        nonlocal calls
        calls += 1
        return sentinel

    clear_runtime_caches()
    monkeypatch.setattr(database, "create_database_engine", create_engine)
    try:
        assert database.get_runtime_engine() is sentinel
        assert database.get_runtime_engine() is sentinel
        assert calls == 1
    finally:
        clear_runtime_caches()


def test_missing_runtime_database_has_safe_domain_error(monkeypatch) -> None:
    clear_runtime_caches()
    monkeypatch.setattr(
        database,
        "create_database_engine",
        lambda _purpose: None,
    )
    try:
        with pytest.raises(DatabaseUnavailableError):
            database.get_runtime_engine()
    finally:
        clear_runtime_caches()


def test_session_closes_on_success_and_rolls_back_on_error(monkeypatch) -> None:
    successful = FakeSession()
    monkeypatch.setattr(
        database,
        "get_runtime_session_factory",
        lambda: lambda: successful,
    )
    dependency = database.get_database_session()
    assert next(dependency) is successful
    with pytest.raises(StopIteration):
        next(dependency)
    assert successful.closed
    assert not successful.rolled_back

    failing = FakeSession()
    monkeypatch.setattr(
        database,
        "get_runtime_session_factory",
        lambda: lambda: failing,
    )
    dependency = database.get_database_session()
    assert next(dependency) is failing
    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))
    assert failing.rolled_back
    assert failing.closed


def test_database_exception_handler_hides_internal_error() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)
    secret = "postgresql+psycopg://user:secret@example.invalid/database"

    @test_app.get("/fails")
    def fails() -> None:
        raise OperationalError("SELECT secret", {}, Exception(secret))

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/fails")

    assert response.status_code == 503
    assert response.json() == {"detail": "数据库服务暂时不可用"}
    assert secret not in response.text
    assert "SELECT" not in response.text


def test_app_timezone_controls_date_boundary() -> None:
    settings = Settings(
        _env_file=None,
        APP_TIMEZONE="Asia/Shanghai",
        DEBUG=False,
    )

    assert current_app_date(
        settings=settings,
        now=datetime(2026, 7, 31, 17, 0, tzinfo=UTC),
    ).isoformat() == "2026-08-01"


def test_invalid_timezone_is_rejected() -> None:
    with pytest.raises(ValueError, match="APP_TIMEZONE"):
        Settings(
            _env_file=None,
            APP_TIMEZONE="Mars/Olympus",
            DEBUG=False,
        )
