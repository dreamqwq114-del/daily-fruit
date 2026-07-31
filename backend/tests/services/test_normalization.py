import pytest

from app.services import (
    InvalidRecommendationInputError,
    NutritionProfile,
    RecommendationFruit,
    normalize_nutrition_profiles,
)


def make_fruit(
    fruit_id: int,
    nutrition: NutritionProfile | None,
) -> RecommendationFruit:
    return RecommendationFruit(
        id=fruit_id,
        name=f"水果{fruit_id}",
        sweet_score=0.5,
        sour_score=0.5,
        soft_score=0.5,
        crisp_score=0.5,
        convenience_score=0.5,
        average_price_level=2,
        nutrition=nutrition,
    )


def profile(value: float) -> NutritionProfile:
    return NutritionProfile(
        energy=value,
        vitamin_c=value,
        fiber=value,
        potassium=value,
        folate=value,
        carotenoids=value,
    )


def test_nutrition_is_normalized_per_feature() -> None:
    normalized = normalize_nutrition_profiles(
        [make_fruit(1, profile(10)), make_fruit(2, profile(30))]
    )

    assert normalized[1] == profile(0.0)
    assert normalized[2] == profile(1.0)


def test_equal_feature_values_use_neutral_score_without_division_by_zero() -> None:
    normalized = normalize_nutrition_profiles(
        [make_fruit(1, profile(10)), make_fruit(2, profile(10))]
    )

    assert normalized[1] == profile(0.5)
    assert normalized[2] == profile(0.5)


def test_missing_nutrition_uses_neutral_profile() -> None:
    normalized = normalize_nutrition_profiles(
        [make_fruit(1, profile(10)), make_fruit(2, None)]
    )

    assert normalized[2] == profile(0.5)


def test_duplicate_fruit_id_is_rejected() -> None:
    with pytest.raises(InvalidRecommendationInputError, match="不能重复"):
        normalize_nutrition_profiles(
            [make_fruit(1, profile(10)), make_fruit(1, profile(20))]
        )


def test_negative_or_non_finite_nutrition_is_rejected() -> None:
    with pytest.raises(InvalidRecommendationInputError, match="非负有限"):
        normalize_nutrition_profiles([make_fruit(1, profile(-1))])

    with pytest.raises(InvalidRecommendationInputError, match="非负有限"):
        normalize_nutrition_profiles([make_fruit(1, profile(float("nan")))])
