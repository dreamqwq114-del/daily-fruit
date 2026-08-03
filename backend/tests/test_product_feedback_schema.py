from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.product_feedback import (
    ProductFeedbackCreate,
    ProductFeedbackRead,
)


def test_product_feedback_schema_strips_content_and_keeps_page_key() -> None:
    payload = ProductFeedbackCreate(
        category="suggestion",
        content="  建议增加更多水果资料。  ",
        page_key="preferences",
    )

    assert payload.content == "建议增加更多水果资料。"
    assert payload.page_key == "preferences"


@pytest.mark.parametrize(
    "payload",
    [
        {"category": "unknown", "content": "无效分类"},
        {"category": "bug", "content": ""},
        {"category": "bug", "content": "   "},
        {"category": "bug", "content": "x" * 1001},
        {"category": "bug", "content": "非法页面", "page_key": "login"},
        {"category": "bug", "content": "多余字段", "user_id": 1},
    ],
)
def test_product_feedback_create_rejects_invalid_payload(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ProductFeedbackCreate.model_validate(payload)


def test_product_feedback_read_omits_user_and_resolution_fields() -> None:
    result = ProductFeedbackRead.model_validate(
        {
            "id": 1,
            "category": "bug",
            "content": "页面偶尔无法加载。",
            "page_key": "today",
            "status": "new",
            "created_at": datetime.now(UTC),
        }
    )

    assert "user_id" not in result.model_dump()
    assert "resolved_at" not in result.model_dump()
