"""Alembic 环境配置。

迁移必须显式指定 ``ALEMBIC_DATABASE_PURPOSE``，只允许 ``migration`` 或
``test``，从而避免误把运行时或 Supabase 正式连接当作测试目标。外部
``auth`` 表只作为 FK 参照，不参与业务 schema 自动生成。
"""

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
    """读取并限制迁移用途，缺失时主动停止。"""

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
    """按用途选择 MIGRATION_DATABASE_URL 或 TEST_DATABASE_URL。"""

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
    """只比较 public schema，并排除 Alembic 自身版本表。"""

    del parent_names
    if type_ == "schema":
        return name in {None, "public"}
    if type_ == "table" and name == "alembic_version":
        return False
    return True


def normalized_foreign_key_signature(
    constraint: ForeignKeyConstraint,
) -> tuple[object, ...]:
    """统一 schema 名称后比较 FK，避免 public 默认值造成假漂移。"""

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
    """忽略标记为 external 的 ORM 表，并使用标准化 FK 比较。"""

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
    """集中设置 schema、类型、默认值和命名比较策略。"""

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
    """生成离线 SQL；仍要求显式迁移用途和 URL。"""

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
    """使用对应用途 engine 连接并在结束时释放连接池。"""

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
    """把现有连接绑定给 Alembic context。"""

    context.configure(
        connection=connection,
        **context_options(),
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
