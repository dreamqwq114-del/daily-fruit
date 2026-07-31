from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.models import Fruit, User
from app.services.recommendation_types import (
    FruitPreference,
    NutritionProfile,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SeasonWindow,
)


def user_to_recommendation_input(user: User) -> RecommendationUser:
    preferences = {
        item.fruit_id: FruitPreference(
            preference_score=float(item.preference_score),
            is_forbidden=item.is_forbidden,
        )
        for item in user.fruit_preferences
    }
    return RecommendationUser(
        region=user.region,
        sweet_preference=float(user.sweet_preference),
        sour_preference=float(user.sour_preference),
        soft_preference=float(user.soft_preference),
        crisp_preference=float(user.crisp_preference),
        price_level=user.price_level,
        convenience_preference=float(user.convenience_preference),
        fruit_preferences=preferences,
    )


def fruit_to_recommendation_input(fruit: Fruit) -> RecommendationFruit:
    nutrition = (
        None
        if fruit.nutrition is None
        else NutritionProfile(
            energy=float(fruit.nutrition.energy),
            vitamin_c=float(fruit.nutrition.vitamin_c),
            fiber=float(fruit.nutrition.fiber),
            potassium=float(fruit.nutrition.potassium),
            folate=float(fruit.nutrition.folate),
            carotenoids=float(fruit.nutrition.carotenoids),
        )
    )
    seasons = tuple(
        SeasonWindow(
            region=item.region,
            start_month=item.start_month,
            end_month=item.end_month,
            season_score=float(item.season_score),
        )
        for item in fruit.seasons
    )
    return RecommendationFruit(
        id=fruit.id,
        name=fruit.name,
        sweet_score=float(fruit.sweet_score),
        sour_score=float(fruit.sour_score),
        soft_score=float(fruit.soft_score),
        crisp_score=float(fruit.crisp_score),
        convenience_score=float(fruit.convenience_score),
        average_price_level=fruit.average_price_level,
        is_active=fruit.is_active,
        nutrition=nutrition,
        seasons=seasons,
    )


def build_recommendation_context(
    *,
    month: int,
    recent_fruit_ids: Sequence[int],
    feedback_by_fruit: Mapping[int, Sequence[str]],
    random_seed: int,
) -> RecommendationContext:
    return RecommendationContext(
        month=month,
        recent_fruit_ids=tuple(recent_fruit_ids),
        feedback_by_fruit={
            fruit_id: tuple(values)
            for fruit_id, values in feedback_by_fruit.items()
        },
        random_seed=random_seed,
    )


__all__ = [
    "build_recommendation_context",
    "fruit_to_recommendation_input",
    "user_to_recommendation_input",
]
