"""Health-only FastAPI Cloud entrypoint for deployment verification."""

from fastapi import FastAPI

from app.main import HealthResponse, health


app = FastAPI(
    title="Daily Fruit API health check",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_api_route(
    "/health",
    health,
    methods=["GET"],
    response_model=HealthResponse,
)
