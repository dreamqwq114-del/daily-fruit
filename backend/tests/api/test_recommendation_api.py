from concurrent.futures import ThreadPoolExecutor
from datetime import date

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_database_session
from app.main import app
from app.models import Recommendation, User
from app.services import recommendation_application_service


TODAY = date(2026, 7, 31)


def valid_user(username: str = "推荐接口测试") -> dict[str, object]:
    return {
        "username": username,
        "city": "苏州",
        "region": "华东",
        "sweet_preference": 0.8,
        "sour_preference": 0.3,
        "soft_preference": 0.4,
        "crisp_preference": 0.8,
        "price_level": 2,
        "convenience_preference": 0.8,
    }


def create_user(client: TestClient, username: str = "推荐接口测试") -> int:
    response = client.post("/api/users", json=valid_user(username))
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(
        recommendation_application_service,
        "current_app_date",
        lambda: TODAY,
    )


def test_today_refresh_feedback_and_history_flow(client: TestClient) -> None:
    user_id = create_user(client)

    first_response = client.get(
        "/api/recommendations/today",
        params={"user_id": user_id},
    )
    assert first_response.status_code == 200
    first = first_response.json()
    assert len(first["items"]) == 2
    assert {item["rank"] for item in first["items"]} == {1, 2}
    assert all(2 <= len(item["reasons"]) <= 4 for item in first["items"])
    assert all(item["fruit"]["nutrition"] for item in first["items"])

    repeated = client.get(
        "/api/recommendations/today",
        params={"user_id": user_id},
    )
    assert repeated.status_code == 200
    assert repeated.json()["id"] == first["id"]

    refreshed_response = client.post(
        "/api/recommendations/refresh",
        json={"user_id": user_id},
    )
    assert refreshed_response.status_code == 201
    refreshed = refreshed_response.json()
    assert refreshed["id"] != first["id"]
    assert refreshed["refresh_number"] == 1
    assert {item["fruit_id"] for item in refreshed["items"]} != {
        item["fruit_id"] for item in first["items"]
    }

    item_id = refreshed["items"][0]["id"]
    feedback = client.post(
        f"/api/recommendations/items/{item_id}/feedback",
        json={"feedback_type": "liked", "comment": "喜欢"},
    )
    assert feedback.status_code == 201
    duplicate = client.post(
        f"/api/recommendations/items/{item_id}/feedback",
        json={"feedback_type": "liked", "comment": "重复点击"},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == feedback.json()["id"]

    history = client.get(f"/api/users/{user_id}/recommendations")
    assert history.status_code == 200
    assert [item["status"] for item in history.json()] == [
        "active",
        "replaced",
    ]
    assert any(
        feedback["feedback_type"] == "change_requested"
        for item in history.json()[1]["items"]
        for feedback in item["feedback"]
    )


@pytest.mark.parametrize(
    "feedback_type",
    [
        "eaten",
        "liked",
        "disliked",
        "unavailable",
        "expensive",
        "tired_of_it",
        "change_requested",
    ],
)
def test_api_accepts_each_feedback_type(
    client: TestClient,
    feedback_type: str,
) -> None:
    user_id = create_user(client, f"反馈-{feedback_type}")
    recommendation = client.get(
        "/api/recommendations/today",
        params={"user_id": user_id},
    ).json()

    response = client.post(
        (
            "/api/recommendations/items/"
            f"{recommendation['items'][0]['id']}/feedback"
        ),
        json={"feedback_type": feedback_type, "comment": ""},
    )

    assert response.status_code == 201
    assert response.json()["feedback_type"] == feedback_type


def test_invalid_resources_and_refresh_state(client: TestClient) -> None:
    assert client.get(
        "/api/recommendations/today",
        params={"user_id": 999999999},
    ).status_code == 404
    assert client.get(
        "/api/recommendations/today",
        params={"user_id": 0},
    ).status_code == 422
    assert client.get(
        "/api/users/999999999/recommendations"
    ).status_code == 404
    assert client.post(
        "/api/recommendations/items/999999999/feedback",
        json={"feedback_type": "liked"},
    ).status_code == 404

    user_id = create_user(client, "没有初始推荐")
    assert client.post(
        "/api/recommendations/refresh",
        json={"user_id": user_id},
    ).status_code == 409


def test_all_forbidden_returns_conflict_without_partial_recommendation(
    client: TestClient,
) -> None:
    user_id = create_user(client, "全部禁用")
    fruits = client.get("/api/fruits").json()
    preferences = [
        {
            "fruit_id": fruit["id"],
            "preference_score": 0,
            "is_forbidden": True,
        }
        for fruit in fruits
    ]
    assert client.put(
        f"/api/users/{user_id}/fruit-preferences",
        json={"preferences": preferences},
    ).status_code == 200

    response = client.get(
        "/api/recommendations/today",
        params={"user_id": user_id},
    )

    assert response.status_code == 409
    assert "不足两种" in response.json()["detail"]
    assert client.get(f"/api/users/{user_id}/recommendations").json() == []


def test_database_error_response_does_not_leak_details() -> None:
    secret = "postgresql+psycopg://user:secret@example.invalid/database"

    def broken_session():
        raise OperationalError("SELECT private", {}, Exception(secret))
        yield

    app.dependency_overrides[get_database_session] = broken_session
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/api/fruits")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "数据库服务暂时不可用"}
    assert secret not in response.text
    assert "SELECT" not in response.text


def test_loaded_today_and_history_have_bounded_query_counts(
    client: TestClient,
    api_engine: Engine,
) -> None:
    user_id = create_user(client, "查询计数")
    client.get(
        "/api/recommendations/today",
        params={"user_id": user_id},
    )
    statements: list[str] = []

    def count_query(*args):
        statements.append(args[2])

    event.listen(api_engine, "before_cursor_execute", count_query)
    try:
        today = client.get(
            "/api/recommendations/today",
            params={"user_id": user_id},
        )
        today_count = _business_query_count(statements)
        statements.clear()
        history = client.get(f"/api/users/{user_id}/recommendations")
        history_count = _business_query_count(statements)
    finally:
        event.remove(api_engine, "before_cursor_execute", count_query)

    assert today.status_code == 200
    assert history.status_code == 200
    assert today_count <= 9
    assert history_count <= 8


def test_concurrent_today_requests_create_one_active_recommendation(
    api_engine: Engine,
) -> None:
    factory = sessionmaker(bind=api_engine, expire_on_commit=False)
    with factory() as setup_session:
        user = User(
            username="并发测试",
            city="苏州",
            region="华东",
            sweet_preference=0.8,
            sour_preference=0.3,
            soft_preference=0.4,
            crisp_preference=0.8,
            price_level=2,
            convenience_preference=0.8,
        )
        setup_session.add(user)
        setup_session.commit()
        user_id = user.id

    def session_dependency():
        with factory() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_database_session] = session_dependency
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(
                    executor.map(
                        lambda _: test_client.get(
                            "/api/recommendations/today",
                            params={"user_id": user_id},
                        ),
                        range(2),
                    )
                )
        assert [response.status_code for response in responses] == [200, 200]
        assert len({response.json()["id"] for response in responses}) == 1
        with factory() as check_session:
            active_count = check_session.execute(
                select(func.count())
                .select_from(Recommendation)
                .where(
                    Recommendation.user_id == user_id,
                    Recommendation.recommendation_date == TODAY,
                    Recommendation.status == "active",
                )
            ).scalar_one()
            assert active_count == 1
            check_session.execute(
                delete(Recommendation).where(Recommendation.user_id == user_id)
            )
            check_session.execute(delete(User).where(User.id == user_id))
            check_session.commit()
    finally:
        app.dependency_overrides.clear()


def _business_query_count(statements: list[str]) -> int:
    transaction_prefixes = (
        "SAVEPOINT",
        "RELEASE SAVEPOINT",
        "ROLLBACK TO SAVEPOINT",
    )
    return sum(
        not statement.lstrip().upper().startswith(transaction_prefixes)
        for statement in statements
    )
