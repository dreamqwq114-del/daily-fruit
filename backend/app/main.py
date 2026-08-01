"""FastAPI 应用入口、CORS、异常处理和健康检查。"""

from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.database import check_database_connection
from app.errors import register_exception_handlers
from app.routers import fruits_router, recommendations_router, users_router


class HealthResponse(BaseModel):
    """不包含连接细节的健康检查响应合同。"""

    status: Literal["ok"]
    environment: str
    database: Literal["not_checked", "not_configured", "ok", "unavailable"]


settings = get_settings()
# 生产环境关闭 docs/openapi，CORS 只允许配置中的 GitHub Pages origin。
app = FastAPI(
    title="Daily Fruit API",
    version="0.1.0",
    debug=settings.debug,
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
    openapi_url=(
        None if settings.app_env == "production" else "/openapi.json"
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(users_router)
app.include_router(fruits_router)
app.include_router(recommendations_router)


@app.get("/health", response_model=HealthResponse)
def health(
    check_database: bool = Query(
        default=False,
        description="Run a safe SELECT 1 without exposing connection details.",
    ),
) -> HealthResponse:
    """报告服务状态；可选执行无写入的 SELECT 1。"""

    database_status = (
        check_database_connection() if check_database else "not_checked"
    )
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        database=database_status,
    )
