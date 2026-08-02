import os
from uuid import uuid4
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.auth import AuthPrincipal, get_current_principal
from app.database import get_database_session
from app.main import app
from app.seed.seed_fruits import load_seed_dataset, seed_database


@pytest.fixture(scope="session")
def api_engine() -> Engine:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    settings = Settings(_env_file=None, TEST_DATABASE_URL=database_url)
    parsed = urlsplit(settings.test_database_url or "")
    assert parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.path.strip("/") == "daily_fruit_test"

    engine = create_engine(database_url)
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one()
    assert version == "0008"
    seed_database(engine, load_seed_dataset())
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM auth.users"))
        engine.dispose()


@pytest.fixture()
def api_session(api_engine: Engine) -> Session:
    connection = api_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def auth_principal() -> AuthPrincipal:
    return AuthPrincipal(auth_user_id=uuid4(), session_id=uuid4())


@pytest.fixture()
def client(
    api_engine: Engine,
    api_session: Session,
    auth_principal: AuthPrincipal,
) -> TestClient:
    with api_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO auth.users (id) VALUES (:id)"),
            {"id": auth_principal.auth_user_id},
        )

    def override_database_session():
        try:
            yield api_session
        except Exception:
            api_session.rollback()
            raise

    app.dependency_overrides[get_database_session] = (
        override_database_session
    )
    app.dependency_overrides[get_current_principal] = lambda: auth_principal
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
