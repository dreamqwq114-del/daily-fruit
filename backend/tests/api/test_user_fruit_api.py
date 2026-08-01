from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


def valid_user() -> dict[str, object]:
    return {
        "username": "api-test-user",
        "city": "Suzhou",
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

    updated = client.put("/api/me", json={"price_level": 3})
    assert updated.status_code == 200
    assert updated.json()["city"] == created["city"]
    assert updated.json()["price_level"] == 3


def test_create_without_city_uses_unknown_default(client: TestClient) -> None:
    payload = {key: value for key, value in valid_user().items() if key != "city"}
    response = client.post("/api/me", json=payload)
    assert response.status_code == 201
    assert response.json()["city"] == "UNKNOWN"


def test_unknown_user_and_invalid_payload_have_clear_status(
    client: TestClient,
) -> None:
    assert client.get("/api/me").status_code == 404
    response = client.post(
        "/api/me",
        json={**valid_user(), "price_level": 9},
    )
    assert response.status_code == 422


def test_preferences_merge_managed_fields_and_preserve_familiarity(
    client: TestClient,
    api_session: Session,
) -> None:
    create_user(client)
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
                    "has_tried": True,
                    "willing_to_try": True,
                },
                {
                    "fruit_id": fruit_ids[1],
                    "preference_score": -1,
                    "is_forbidden": True,
                    "has_tried": True,
                    "willing_to_try": False,
                },
            ]
        },
    )
    assert first.status_code == 200
    assert len(first.json()) == 2
    assert first.json()[0]["has_tried"] is True
    assert first.json()[1]["willing_to_try"] is False

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
    assert [item["fruit_id"] for item in replaced.json()] == fruit_ids
    by_fruit = {item["fruit_id"]: item for item in replaced.json()}
    assert by_fruit[fruit_ids[0]]["preference_score"] == 1
    assert by_fruit[fruit_ids[0]]["has_tried"] is True
    assert by_fruit[fruit_ids[1]]["preference_score"] is None
    assert by_fruit[fruit_ids[1]]["is_forbidden"] is False
    assert by_fruit[fruit_ids[1]]["has_tried"] is True
    assert by_fruit[fruit_ids[1]]["willing_to_try"] is False

    missing = client.put(
        "/api/me/fruit-preferences",
        json={"preferences": [{"fruit_id": 999999999}]},
    )
    assert missing.status_code == 404
    unchanged = client.get("/api/me/fruit-preferences")
    assert [item["fruit_id"] for item in unchanged.json()] == fruit_ids

    cleared = client.put(
        "/api/me/fruit-preferences",
        json={"preferences": []},
    )
    assert cleared.status_code == 200
    cleared_by_fruit = {item["fruit_id"]: item for item in cleared.json()}
    assert set(cleared_by_fruit) == set(fruit_ids)
    assert all(
        item["preference_score"] is None
        for item in cleared_by_fruit.values()
    )
    assert all(
        item["is_forbidden"] is False
        for item in cleared_by_fruit.values()
    )
    assert all(item["has_tried"] is True for item in cleared_by_fruit.values())


def test_preferences_reject_too_many_favorites_and_conflicts(
    client: TestClient,
) -> None:
    create_user(client)
    fruits = client.get("/api/fruits").json()[:6]
    too_many = client.put(
        "/api/me/fruit-preferences",
        json={
            "preferences": [
                {"fruit_id": fruit["id"], "preference_score": 2}
                for fruit in fruits
            ]
        },
    )
    assert too_many.status_code == 422

    conflict = client.put(
        "/api/me/fruit-preferences",
        json={
            "preferences": [
                {
                    "fruit_id": fruits[0]["id"],
                    "preference_score": 2,
                    "is_forbidden": True,
                }
            ]
        },
    )
    assert conflict.status_code == 422


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
