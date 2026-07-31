from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings


def create_database_engine() -> Engine | None:
    database_url = get_settings().database_url
    if not database_url:
        return None
    return create_engine(database_url, pool_pre_ping=True)


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
