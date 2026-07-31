from logging.config import fileConfig
import os
from typing import Any, Literal

from alembic import context
from sqlalchemy import ForeignKeyConstraint
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
    if type_ == "table" and name == "alembic_version":
        return False
    return True


def normalized_foreign_key_signature(
    constraint: ForeignKeyConstraint,
) -> tuple[object, ...]:
    def normalize_target(target: str) -> tuple[str, ...]:
        parts = tuple(target.split("."))
        if len(parts) == 2:
            return ("public", *parts)
        return parts

    source_schema = constraint.table.schema or "public"
    return (
        source_schema,
        constraint.table.name,
        tuple(element.parent.name for element in constraint.elements),
        tuple(
            normalize_target(element.target_fullname)
            for element in constraint.elements
        ),
        constraint.onupdate,
        constraint.ondelete,
        constraint.deferrable,
        constraint.initially,
    )


def include_object(
    object_: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    del name, reflected
    if getattr(object_, "info", {}).get("external") is True:
        return False
    if (
        type_ == "foreign_key_constraint"
        and isinstance(object_, ForeignKeyConstraint)
        and isinstance(compare_to, ForeignKeyConstraint)
    ):
        return normalized_foreign_key_signature(
            object_
        ) != normalized_foreign_key_signature(compare_to)
    return True


def context_options() -> dict[str, Any]:
    return {
        "target_metadata": target_metadata,
        "include_schemas": True,
        "include_name": include_name,
        "include_object": include_object,
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
