from fastapi.testclient import TestClient

from app import database
from app.main import app


client = TestClient(app)


def test_health_does_not_require_database() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": "development",
        "database": "not_checked",
    }


def test_health_reports_missing_database_configuration_safely() -> None:
    response = client.get("/health?check_database=true")

    assert response.status_code == 200
    assert response.json()["database"] == "not_configured"
    assert "DATABASE_URL" not in response.text
    assert "postgresql" not in response.text


def test_health_hides_invalid_database_configuration(monkeypatch) -> None:
    invalid_secret = "this-is-not-a-database-url"
    monkeypatch.setattr(
        database,
        "create_database_engine",
        lambda: (_ for _ in ()).throw(ValueError(invalid_secret)),
    )

    response = client.get("/health?check_database=true")

    assert response.status_code == 200
    assert response.json()["database"] == "unavailable"
    assert invalid_secret not in response.text
