from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


def valid_user() -> dict[str, object]:
    return {
        "username": "接口测试用户",
        "city": "苏州",
        "region": "华东",
        "sweet_preference": 0.8,
        "sour_preference": 0.3,
        "soft_preference": 0.4,
        "crisp_preference": 0.9,
        "price_level": 2,
        "convenience_preference": 0.8,
    }


def create_user(client: TestClient) -> dict[str, object]:
    response = client.post("/api/me", json=valid_user())
    assert response.status_code == 201
    return response.json()


def test_create_get_and_update_user(client: TestClient) -> None:
    created = create_user(client)

    fetched = client.get("/api/me")
    assert fetched.status_code == 200
    assert fetched.json() == created

    updated = client.put(
        "/api/me",
        json={"city": "上海", "price_level": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "上海"
    assert updated.json()["price_level"] == 3


def test_unknown_user_and_invalid_payload_have_clear_status(
    client: TestClient,
) -> None:
    assert client.get("/api/me").status_code == 404
    response = client.post(
        "/api/me",
        json={**valid_user(), "price_level": 9},
    )
    assert response.status_code == 422


def test_preferences_are_fully_replaced_and_validate_fruits(
    client: TestClient,
    api_session: Session,
) -> None:
    user = create_user(client)
    fruit_ids = list(
        api_session.execute(
            text("SELECT id FROM public.fruits ORDER BY id LIMIT 2")
        ).scalars()
    )
    assert len(fruit_ids) == 2

    first = client.put(
        "/api/me/fruit-preferences",
        json={
            "preferences": [
                {
                    "fruit_id": fruit_ids[0],
                    "preference_score": 2,
                    "is_forbidden": False,
                },
                {
                    "fruit_id": fruit_ids[1],
                    "preference_score": 0,
                    "is_forbidden": True,
                },
            ]
        },
    )
    assert first.status_code == 200
    assert len(first.json()) == 2

    replaced = client.put(
        "/api/me/fruit-preferences",
        json={
            "preferences": [
                {
                    "fruit_id": fruit_ids[0],
                    "preference_score": 1,
                    "is_forbidden": False,
                }
            ]
        },
    )
    assert replaced.status_code == 200
    assert [item["fruit_id"] for item in replaced.json()] == [fruit_ids[0]]

    missing = client.put(
        "/api/me/fruit-preferences",
        json={"preferences": [{"fruit_id": 999999999}]},
    )
    assert missing.status_code == 404
    unchanged = client.get(
        "/api/me/fruit-preferences"
    )
    assert [item["fruit_id"] for item in unchanged.json()] == [fruit_ids[0]]

    cleared = client.put(
        "/api/me/fruit-preferences",
        json={"preferences": []},
    )
    assert cleared.status_code == 200
    assert cleared.json() == []


def test_fruit_list_and_detail_hide_inactive(
    client: TestClient,
    api_session: Session,
) -> None:
    response = client.get("/api/fruits")
    assert response.status_code == 200
    fruits = response.json()
    assert len(fruits) == 24
    assert all(item["is_active"] for item in fruits)

    detail = client.get(f"/api/fruits/{fruits[0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["nutrition"] is not None
    assert len(detail.json()["seasons"]) >= 1

    inactive_id = fruits[0]["id"]
    api_session.execute(
        text("UPDATE public.fruits SET is_active=false WHERE id=:id"),
        {"id": inactive_id},
    )
    api_session.commit()
    assert client.get(f"/api/fruits/{inactive_id}").status_code == 404
    listed_ids = {item["id"] for item in client.get("/api/fruits").json()}
    assert inactive_id not in listed_ids
