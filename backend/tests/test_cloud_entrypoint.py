import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_cloud_entrypoint_exposes_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/me"),
        ("GET", "/api/fruits"),
        ("GET", "/api/recommendations/today"),
    ],
)
def test_application_rejects_anonymous_business_api(
    method: str,
    path: str,
) -> None:
    response = client.request(method, path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_test_environment_keeps_local_api_docs() -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
