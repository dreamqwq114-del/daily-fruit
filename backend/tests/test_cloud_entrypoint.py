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
        ("POST", "/api/users"),
        ("GET", "/api/fruits"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
    ],
)
def test_cloud_entrypoint_hides_business_api(
    method: str,
    path: str,
) -> None:
    response = client.request(method, path)

    assert response.status_code == 404
