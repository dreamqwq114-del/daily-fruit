import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import (
    FruitBase,
    FruitNutritionBase,
    FruitSeasonBase,
    RecommendationCreate,
    RecommendationFeedbackCreate,
    RecommendationReason,
    UserCreate,
    UserFruitPreferenceInput,
    UserFruitPreferenceRead,
    UserFruitPreferencesUpdate,
    UserUpdate,
)


def valid_user_data() -> dict[str, object]:
    return {
        "username": "小果",
        "city": "苏州",
        "region": "华东",
        "sweet_preference": "0.800",
        "sour_preference": "0.300",
        "soft_preference": "0.400",
        "crisp_preference": "0.900",
        "price_level": 2,
        "convenience_preference": "0.700",
    }


def valid_fruit_data() -> dict[str, object]:
    return {
        "name": "苹果",
        "category": "仁果",
        "taste": "清甜、脆",
        "sweet_score": "0.700",
        "sour_score": "0.300",
        "soft_score": "0.200",
        "crisp_score": "0.900",
        "convenience_score": "0.800",
        "average_price_level": 2,
        "default_portion": "1 个中等大小",
        "image_url": None,
        "description": "常见演示水果",
        "is_active": True,
    }


def valid_reasons() -> list[dict[str, str]]:
    return [
        {
            "code": "in_season",
            "message": "当前处于适宜购买月份",
            "component": "season_score",
        },
        {
            "code": "price_match",
            "message": "符合你的价格范围",
            "component": "price_match_score",
        },
    ]


def valid_recommendation_data() -> dict[str, object]:
    return {
        "user_id": 1,
        "recommendation_date": "2026-07-31",
        "refresh_number": 0,
        "total_score": "0.812500",
        "status": "active",
        "items": [
            {
                "fruit_id": 1,
                "score": "0.850000",
                "rank": 1,
                "reasons": valid_reasons(),
            },
            {
                "fruit_id": 2,
                "score": "0.775000",
                "rank": 2,
                "reasons": valid_reasons(),
            },
        ],
    }


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("sweet_preference", "-0.001"),
        ("sour_preference", "1.001"),
        ("soft_preference", "0.0001"),
        ("price_level", 4),
    ],
)
def test_user_rejects_out_of_range_values(
    field_name: str,
    invalid_value: object,
) -> None:
    data = valid_user_data()
    data[field_name] = invalid_value

    with pytest.raises(ValidationError):
        UserCreate.model_validate(data)


def test_user_update_requires_non_null_changes() -> None:
    with pytest.raises(ValidationError, match="At least one"):
        UserUpdate.model_validate({})

    with pytest.raises(ValidationError, match="must not be null"):
        UserUpdate.model_validate({"city": None})

    update = UserUpdate.model_validate({"city": "  上海  "})
    assert update.model_dump(exclude_unset=True) == {"city": "上海"}


def test_user_create_allows_omitted_city_and_validates_horizon() -> None:
    data = valid_user_data()
    data.pop("city")
    data["consumption_horizon_days"] = 7
    created = UserCreate.model_validate(data)
    assert created.city == "UNKNOWN"
    assert created.consumption_horizon_days == 7

    invalid = {**data, "consumption_horizon_days": 3}
    with pytest.raises(ValidationError):
        UserCreate.model_validate(invalid)


def test_user_purchase_condition_defaults_and_validation() -> None:
    created = UserCreate.model_validate(valid_user_data())
    assert created.market_access_level == 2
    assert created.accepts_online_purchase is False

    updated = UserUpdate.model_validate(
        {
            "market_access_level": 1,
            "accepts_online_purchase": True,
        }
    )
    assert updated.model_dump(exclude_unset=True) == {
        "market_access_level": 1,
        "accepts_online_purchase": True,
    }

    for invalid_level in (0, 4, "2"):
        with pytest.raises(ValidationError):
            UserUpdate.model_validate({"market_access_level": invalid_level})

    with pytest.raises(ValidationError):
        UserUpdate.model_validate({"accepts_online_purchase": "true"})


def test_fruit_scores_and_price_are_validated() -> None:
    fruit = FruitBase.model_validate(valid_fruit_data())
    assert fruit.name == "苹果"

    invalid = valid_fruit_data()
    invalid["convenience_score"] = "1.100"
    with pytest.raises(ValidationError):
        FruitBase.model_validate(invalid)


@pytest.mark.parametrize("month", [0, 13])
def test_season_rejects_invalid_month(month: int) -> None:
    with pytest.raises(ValidationError):
        FruitSeasonBase.model_validate(
            {
                "region": "华东",
                "start_month": month,
                "end_month": 10,
                "season_score": "0.900",
            }
        )


def test_season_accepts_boundary_and_cross_year_months() -> None:
    season = FruitSeasonBase.model_validate(
        {
            "region": "华东",
            "start_month": 12,
            "end_month": 1,
            "season_score": "1.000",
        }
    )

    assert season.start_month == 12
    assert season.end_month == 1


def test_nutrition_rejects_negative_values() -> None:
    with pytest.raises(ValidationError):
        FruitNutritionBase.model_validate(
            {
                "energy": "50.00",
                "vitamin_c": "10.00",
                "fiber": "-0.01",
                "potassium": "100.00",
                "folate": "5.00",
                "carotenoids": "1.00",
            }
        )


@pytest.mark.parametrize("score", ["-1.01", "2.01"])
def test_fruit_preference_rejects_out_of_range_score(score: str) -> None:
    with pytest.raises(ValidationError):
        UserFruitPreferenceInput.model_validate(
            {
                "fruit_id": 1,
                "preference_score": score,
                "is_forbidden": False,
            }
        )


def test_fruit_preference_rejects_untried_favorite_combination() -> None:
    with pytest.raises(ValidationError, match="especially loved"):
        UserFruitPreferenceInput.model_validate(
            {
                "fruit_id": 1,
                "preference_score": 2,
                "has_tried": False,
            }
        )


def test_fruit_preference_rejects_favorite_forbidden_conflict() -> None:
    with pytest.raises(ValidationError, match="both"):
        UserFruitPreferenceInput.model_validate(
            {
                "fruit_id": 1,
                "preference_score": 2,
                "is_forbidden": True,
            }
        )


def test_preference_batch_rejects_more_than_five_favorites() -> None:
    with pytest.raises(ValidationError, match="five"):
        UserFruitPreferencesUpdate.model_validate(
            {
                "preferences": [
                    {"fruit_id": fruit_id, "preference_score": 2}
                    for fruit_id in range(1, 7)
                ]
            }
        )


def test_preference_batch_rejects_duplicate_fruit_ids() -> None:
    with pytest.raises(ValidationError, match="only once"):
        UserFruitPreferencesUpdate.model_validate(
            {
                "preferences": [
                    {"fruit_id": 1, "preference_score": 1},
                    {"fruit_id": 1, "preference_score": 2},
                ]
            }
        )


def test_reason_structure_is_strict_and_has_stable_field_order() -> None:
    reason = RecommendationReason.model_validate(valid_reasons()[0])
    payload = json.loads(reason.model_dump_json())

    assert list(payload) == ["code", "message", "component", "contribution"]
    assert payload == {**valid_reasons()[0], "contribution": 0.0}

    with pytest.raises(ValidationError):
        RecommendationReason.model_validate(
            {**valid_reasons()[0], "medical_claim": "治疗疾病"}
        )


@pytest.mark.parametrize("reason_count", [1, 5])
def test_recommendation_item_requires_two_to_four_reasons(
    reason_count: int,
) -> None:
    data = valid_recommendation_data()
    data["items"][0]["reasons"] = valid_reasons()[:1] * reason_count

    with pytest.raises(ValidationError):
        RecommendationCreate.model_validate(data)


def test_recommendation_requires_two_distinct_ranked_fruits() -> None:
    duplicate_fruit = valid_recommendation_data()
    duplicate_fruit["items"][1]["fruit_id"] = 1
    with pytest.raises(ValidationError, match="distinct fruits"):
        RecommendationCreate.model_validate(duplicate_fruit)

    duplicate_rank = valid_recommendation_data()
    duplicate_rank["items"][1]["rank"] = 1
    with pytest.raises(ValidationError, match="ranks 1 and 2"):
        RecommendationCreate.model_validate(duplicate_rank)


@pytest.mark.parametrize("item_count", [1, 3])
def test_recommendation_requires_exactly_two_items(item_count: int) -> None:
    data = valid_recommendation_data()
    data["items"] = data["items"][:1] * item_count

    with pytest.raises(ValidationError):
        RecommendationCreate.model_validate(data)


def test_recommendation_rejects_invalid_scores_and_refresh_number() -> None:
    invalid_total = valid_recommendation_data()
    invalid_total["total_score"] = "1.000001"
    with pytest.raises(ValidationError):
        RecommendationCreate.model_validate(invalid_total)

    invalid_item = valid_recommendation_data()
    invalid_item["items"][0]["score"] = "-0.000001"
    with pytest.raises(ValidationError):
        RecommendationCreate.model_validate(invalid_item)

    invalid_refresh = valid_recommendation_data()
    invalid_refresh["refresh_number"] = -1
    with pytest.raises(ValidationError):
        RecommendationCreate.model_validate(invalid_refresh)


@pytest.mark.parametrize("status", ["pending", "deleted", "ACTIVE"])
def test_recommendation_rejects_invalid_status(status: str) -> None:
    data = valid_recommendation_data()
    data["status"] = status

    with pytest.raises(ValidationError):
        RecommendationCreate.model_validate(data)


def test_recommendation_json_serializes_decimal_scores_as_numbers() -> None:
    recommendation = RecommendationCreate.model_validate(
        valid_recommendation_data()
    )
    payload = json.loads(recommendation.model_dump_json())

    assert payload["total_score"] == pytest.approx(0.8125)
    assert payload["items"][0]["score"] == pytest.approx(0.85)
    assert isinstance(payload["total_score"], float)


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
def test_feedback_accepts_each_supported_type(feedback_type: str) -> None:
    feedback = RecommendationFeedbackCreate.model_validate(
        {"feedback_type": feedback_type, "comment": ""}
    )
    assert feedback.feedback_type == feedback_type


def test_feedback_rejects_unknown_type_and_long_comment() -> None:
    with pytest.raises(ValidationError):
        RecommendationFeedbackCreate.model_validate(
            {"feedback_type": "cured_me", "comment": ""}
        )

    with pytest.raises(ValidationError):
        RecommendationFeedbackCreate.model_validate(
            {"feedback_type": "liked", "comment": "x" * 1001}
        )


def test_read_schema_supports_orm_attributes_and_aware_timestamps() -> None:
    now = datetime.now(UTC)
    orm_preference = SimpleNamespace(
        id=1,
        user_id=2,
        fruit_id=3,
        preference_score=Decimal("1.00"),
        is_forbidden=False,
        created_at=now,
        updated_at=now,
    )

    result = UserFruitPreferenceRead.model_validate(orm_preference)

    assert result.id == 1
    assert result.created_at.tzinfo is not None

    orm_preference.created_at = datetime.now()
    with pytest.raises(ValidationError):
        UserFruitPreferenceRead.model_validate(orm_preference)
