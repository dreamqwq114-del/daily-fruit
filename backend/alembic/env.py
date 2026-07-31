from logging.config import fileConfig
import os
from typing import Any, Literal

from alembic import context
from sqlalchemy.engine import Connection

from app.config import Settings, get_settings
from app.database import create_database_engine
from app.models import Base


AlembicPurpose = Literal["migration", "test"]
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_alembic_purpose() -> AlembicPurpose:
    purpose = os.getenv("ALEMBIC_DATABASE_PURPOSE", "").strip().lower()
    if purpose not in {"migration", "test"}:
        raise RuntimeError(
            "ALEMBIC_DATABASE_PURPOSE must be explicitly set to "
            "migration or test"
        )
    return purpose


def get_alembic_url(
    purpose: AlembicPurpose,
    settings: Settings,
) -> str:
    database_url = settings.database_url_for(purpose)
    if database_url is None:
        variable_name = (
            "MIGRATION_DATABASE_URL"
            if purpose == "migration"
            else "TEST_DATABASE_URL"
        )
        raise RuntimeError(f"{variable_name} is not configured")
    return database_url


def include_name(
    name: str | None,
    type_: str,
    parent_names: dict[str, str | None],
) -> bool:
    del parent_names
    if type_ == "schema":
        return name in {None, "public"}
    return True


def context_options() -> dict[str, Any]:
    return {
        "target_metadata": target_metadata,
        "include_schemas": True,
        "include_name": include_name,
        "compare_type": True,
        "compare_server_default": True,
        "version_table_schema": "public",
    }


def run_migrations_offline() -> None:
    purpose = get_alembic_purpose()
    database_url = get_alembic_url(purpose, get_settings())
    context.configure(
        url=database_url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **context_options(),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    purpose = get_alembic_purpose()
    settings = get_settings()
    get_alembic_url(purpose, settings)
    engine = create_database_engine(purpose, settings=settings)
    if engine is None:
        raise RuntimeError("Alembic database URL is not configured")

    try:
        with engine.connect() as connection:
            configure_online_context(connection)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


def configure_online_context(connection: Connection) -> None:
    context.configure(
        connection=connection,
        **context_options(),
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
