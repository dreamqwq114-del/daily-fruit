"""SQLAlchemy engine/session 工厂及安全的数据库健康检查。

``runtime`` 使用连接池，``migration`` 和 ``test`` 使用 ``NullPool``，
避免 Alembic 或一次性测试连接长期占用 FastAPI 的连接资源。模块只在
健康检查中返回状态词，不会把连接串、密码或底层异常返回给客户端。
"""

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
    """按用途创建 PostgreSQL engine；未配置 URL 时返回 ``None``。"""

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
    """执行无副作用的 ``SELECT 1``，只返回安全的状态枚举。"""

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
    """获取缓存的 FastAPI 运行时 engine，并把配置错误转换为 503。"""

    try:
        engine = create_database_engine("runtime")
    except (SQLAlchemyError, ValueError) as error:
        raise DatabaseUnavailableError() from error
    if engine is None:
        raise DatabaseUnavailableError()
    return engine


@lru_cache
def get_runtime_session_factory() -> sessionmaker[Session]:
    """创建不自动提交的 Session 工厂，事务由 service 显式提交或回滚。"""

    return sessionmaker(
        bind=get_runtime_engine(),
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def get_database_session() -> Iterator[Session]:
    """FastAPI 依赖：请求结束关闭 Session，异常时先回滚。"""

    session = get_runtime_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_runtime_database() -> None:
    """测试或进程重载时释放缓存 engine，避免连接泄漏。"""

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
