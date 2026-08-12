import pytest
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
    assert created["market_access_level"] == 2
    assert created["accepts_online_purchase"] is False

    updated = client.put(
        "/api/me",
        json={
            "price_level": 3,
            "market_access_level": 1,
            "accepts_online_purchase": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == created["city"]
    assert updated.json()["price_level"] == 3
    assert updated.json()["market_access_level"] == 1
    assert updated.json()["accepts_online_purchase"] is True

    partial = client.put("/api/me", json={"price_level": 2})
    assert partial.status_code == 200
    assert partial.json()["market_access_level"] == 1
    assert partial.json()["accepts_online_purchase"] is True


def test_purchase_condition_rejects_invalid_values(client: TestClient) -> None:
    create_user(client)

    assert client.put("/api/me", json={"market_access_level": 0}).status_code == 422
    assert client.put("/api/me", json={"market_access_level": 4}).status_code == 422
    assert client.put(
        "/api/me",
        json={"accepts_online_purchase": "true"},
    ).status_code == 422


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
                },
                {
                    "fruit_id": fruit_ids[1],
                    "preference_score": -1,
                    "is_forbidden": True,
                    "has_tried": False,
                    "willing_to_try": False,
                },
            ]
        },
    )
    assert first.status_code == 200
    assert len(first.json()) == 2
    assert first.json()[0]["has_tried"] is True
    assert first.json()[0]["willing_to_try"] is None
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
    assert by_fruit[fruit_ids[1]]["has_tried"] is False
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
    assert cleared_by_fruit[fruit_ids[0]]["has_tried"] is True
    assert cleared_by_fruit[fruit_ids[1]]["has_tried"] is False


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


def test_favorite_transition_sets_tried_and_clears_stale_willingness(
    client: TestClient,
    api_session: Session,
) -> None:
    create_user(client)
    fruit_id = api_session.execute(
        text("SELECT id FROM public.fruits ORDER BY id LIMIT 1")
    ).scalar_one()

    initial = client.put(
        "/api/me/fruit-preferences",
        json={
            "preferences": [
                {
                    "fruit_id": fruit_id,
                    "preference_score": None,
                    "has_tried": False,
                    "willing_to_try": False,
                }
            ]
        },
    )
    assert initial.status_code == 200

    favorite = client.put(
        "/api/me/fruit-preferences",
        json={
            "preferences": [
                {"fruit_id": fruit_id, "preference_score": 2}
            ]
        },
    )
    assert favorite.status_code == 200
    assert favorite.json()[0]["has_tried"] is True
    assert favorite.json()[0]["willing_to_try"] is None
    persisted = client.get("/api/me/fruit-preferences")
    assert persisted.status_code == 200
    assert persisted.json()[0]["has_tried"] is True
    assert persisted.json()[0]["willing_to_try"] is None


@pytest.mark.parametrize("has_tried", [True, None])
@pytest.mark.parametrize("willing_to_try", [True, False])
def test_willingness_requires_explicitly_untried_state(
    client: TestClient,
    api_session: Session,
    has_tried: bool | None,
    willing_to_try: bool,
) -> None:
    create_user(client)
    fruit_id = api_session.execute(
        text("SELECT id FROM public.fruits ORDER BY id LIMIT 1")
    ).scalar_one()

    response = client.put(
        "/api/me/fruit-preferences",
        json={
            "preferences": [
                {
                    "fruit_id": fruit_id,
                    "preference_score": 1,
                    "has_tried": has_tried,
                    "willing_to_try": willing_to_try,
                }
            ]
        },
    )
    assert response.status_code == 422


def test_setting_tried_clears_legacy_willingness(
    client: TestClient,
    api_session: Session,
) -> None:
    create_user(client)
    fruit_id = api_session.execute(
        text("SELECT id FROM public.fruits ORDER BY id LIMIT 1")
    ).scalar_one()
    assert client.put(
        "/api/me/fruit-preferences",
        json={
            "preferences": [{
                "fruit_id": fruit_id,
                "has_tried": False,
                "willing_to_try": True,
            }]
        },
    ).status_code == 200

    updated = client.put(
        "/api/me/fruit-preferences",
        json={
            "preferences": [{
                "fruit_id": fruit_id,
                "has_tried": True,
            }]
        },
    )
    assert updated.status_code == 200
    assert updated.json()[0]["has_tried"] is True
    assert updated.json()[0]["willing_to_try"] is None


def test_fruit_list_and_detail_hide_inactive(
    client: TestClient,
    api_session: Session,
) -> None:
    response = client.get("/api/fruits")
    assert response.status_code == 200
    fruits = response.json()
    assert len(fruits) == 24
    assert all(item["is_active"] for item in fruits)
    modes_by_code = {
        item["code"]: item["selection_matching_mode"]
        for item in fruits
    }
    assert modes_by_code["apple"] == "texture"
    assert modes_by_code["peach"] == "texture"
    assert modes_by_code["grape"] == "texture"
    assert modes_by_code["kiwifruit"] == "sweet-sour"
    assert modes_by_code["pomegranate"] == "explicit-only"
    assert modes_by_code["dragon_fruit"] == "explicit-only"
    effects_by_code = {
        item["code"]: item["selection_option_score_effect"]
        for item in fruits
    }
    assert effects_by_code["pomegranate"] == "filter-only"
    assert effects_by_code["dragon_fruit"] == "profile-override"
    assert effects_by_code["apple"] == "profile-override"

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
