from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import ProductFeedback


def valid_user(username: str = "反馈测试用户") -> dict[str, object]:
    return {
        "username": username,
        "city": "苏州",
        "region": "华东",
        "price_level": 2,
        "convenience_preference": 0.7,
    }


def test_product_feedback_requires_business_profile(client: TestClient) -> None:
    response = client.post(
        "/api/product-feedback",
        json={
            "category": "bug",
            "content": "尚未建立资料时不能提交。",
            "page_key": "today",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "尚未创建用户资料"}


def test_product_feedback_uses_current_user_and_returns_safe_response(
    client: TestClient,
    api_session,
) -> None:
    assert client.post("/api/me", json=valid_user()).status_code == 201

    response = client.post(
        "/api/product-feedback",
        json={
            "category": "bug",
            "content": "点击换一组后一直显示加载状态。",
            "page_key": "today",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "bug"
    assert body["content"] == "点击换一组后一直显示加载状态。"
    assert body["page_key"] == "today"
    assert body["status"] == "new"
    assert "user_id" not in body
    assert "resolved_at" not in body

    stored = api_session.execute(select(ProductFeedback)).scalar_one()
    assert stored.user_id is not None
    assert stored.category == "bug"
    assert stored.status == "new"


def test_product_feedback_rejects_client_owned_fields(
    client: TestClient,
) -> None:
    assert client.post("/api/me", json=valid_user()).status_code == 201

    response = client.post(
        "/api/product-feedback",
        json={
            "category": "suggestion",
            "content": "不应接受客户端状态字段。",
            "user_id": 999,
            "status": "resolved",
        },
    )

    assert response.status_code == 422


def test_product_feedback_validates_content_and_page_key(
    client: TestClient,
) -> None:
    assert client.post("/api/me", json=valid_user()).status_code == 201

    for content in ("", "   ", "x" * 1001):
        response = client.post(
            "/api/product-feedback",
            json={"category": "other", "content": content},
        )
        assert response.status_code == 422

    response = client.post(
        "/api/product-feedback",
        json={
            "category": "other",
            "content": "未知页面来源也必须由后端拒绝。",
            "page_key": "login",
        },
    )
    assert response.status_code == 422
