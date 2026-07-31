from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.database import check_database_connection


class HealthResponse(BaseModel):
    status: Literal["ok"]
    environment: str
    database: Literal["not_checked", "not_configured", "ok", "unavailable"]


settings = get_settings()
app = FastAPI(
    title="Daily Fruit API",
    version="0.1.0",
    debug=settings.debug,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health(
    check_database: bool = Query(
        default=False,
        description="Run a safe SELECT 1 without exposing connection details.",
    ),
) -> HealthResponse:
    database_status = (
        check_database_connection() if check_database else "not_checked"
    )
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        database=database_status,
    )

