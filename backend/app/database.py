from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import DatabasePurpose, Settings, get_settings
from app.errors import DatabaseUnavailableError


def create_database_engine(
    purpose: DatabasePurpose = "runtime",
    *,
    settings: Settings | None = None,
) -> Engine | None:
    active_settings = settings or get_settings()
    database_url = active_settings.database_url_for(purpose)
    if not database_url:
        return None

    engine_options: dict[str, object] = {
        "connect_args": {
            "connect_timeout": (
                active_settings.database_connect_timeout_seconds
            ),
        },
    }
    if purpose == "runtime":
        engine_options.update(
            pool_pre_ping=True,
            pool_size=active_settings.database_pool_size,
            max_overflow=active_settings.database_max_overflow,
        )
    else:
        engine_options["poolclass"] = NullPool

    return create_engine(database_url, **engine_options)


def check_database_connection() -> str:
    engine: Engine | None = None

    try:
        engine = create_database_engine()
        if engine is None:
            return "not_configured"

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, ValueError):
        return "unavailable"
    finally:
        if engine is not None:
            engine.dispose()

    return "ok"


@lru_cache
def get_runtime_engine() -> Engine:
    try:
        engine = create_database_engine("runtime")
    except (SQLAlchemyError, ValueError) as error:
        raise DatabaseUnavailableError() from error
    if engine is None:
        raise DatabaseUnavailableError()
    return engine


@lru_cache
def get_runtime_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_runtime_engine(),
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def get_database_session() -> Iterator[Session]:
    session = get_runtime_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_runtime_database() -> None:
    if get_runtime_engine.cache_info().currsize:
        get_runtime_engine().dispose()
    get_runtime_session_factory.cache_clear()
    get_runtime_engine.cache_clear()


__all__ = [
    "check_database_connection",
    "create_database_engine",
    "dispose_runtime_database",
    "get_database_session",
    "get_runtime_engine",
    "get_runtime_session_factory",
]
