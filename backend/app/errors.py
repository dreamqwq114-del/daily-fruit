from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class ApplicationError(Exception):
    status_code = 400
    default_detail = "请求无法完成"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.default_detail)
        self.detail = detail or self.default_detail


class ResourceNotFoundError(ApplicationError):
    status_code = 404
    default_detail = "请求的资源不存在"


class ResourceConflictError(ApplicationError):
    status_code = 409
    default_detail = "当前资源状态无法完成该操作"


class DatabaseUnavailableError(ApplicationError):
    status_code = 503
    default_detail = "数据库服务暂时不可用"


class AuthenticationError(ApplicationError):
    status_code = 401
    default_detail = "登录状态无效或已过期"
    headers = {"WWW-Authenticate": "Bearer"}


class AuthenticationUnavailableError(ApplicationError):
    status_code = 503
    default_detail = "认证服务暂时不可用"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(
        _request: Request,
        error: ApplicationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail},
            headers=error.headers,
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        _request: Request,
        _error: SQLAlchemyError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": DatabaseUnavailableError.default_detail},
        )


__all__ = [
    "ApplicationError",
    "AuthenticationError",
    "AuthenticationUnavailableError",
    "DatabaseUnavailableError",
    "ResourceConflictError",
    "ResourceNotFoundError",
    "register_exception_handlers",
]
