from datetime import date, datetime, timedelta, timezone

import pytest

from app.services import (
    FeedbackEvent,
    FruitPreference,
    HistoryEvent,
    NutritionProfile,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SeasonWindow,
    filter_eligible_fruits,
    normalize_nutrition_profiles,
    recommend_fruits,
    score_candidates,
    select_recommendation_pair,
)
from app.services.recommendation_service import InvalidRecommendationInputError


def user(**changes: object) -> RecommendationUser:
    values: dict[str, object] = {
        "region": "华东",
        "sweet_preference": 0.7,
        "sour_preference": 0.4,
        "soft_preference": 0.4,
        "crisp_preference": 0.7,
        "price_level": 2,
        "convenience_preference": 0.6,
    }
    values.update(changes)
    return RecommendationUser(**values)


def fruit(
    fruit_id: int,
    *,
    category: str = "berry",
    price: int = 2,
    role: str = "main",
    seasons: tuple[SeasonWindow, ...] = (),
    nutrition: NutritionProfile | None = NutritionProfile(
        energy=50,
        vitamin_c=20,
        fiber=2,
        potassium=100,
        folate=10,
        carotenoids=1,
    ),
    **changes: object,
) -> RecommendationFruit:
    values: dict[str, object] = {
        "id": fruit_id,
        "name": f"水果{fruit_id}",
        "category": category,
        "sweet_score": 0.7,
        "sour_score": 0.4,
        "soft_score": 0.4,
        "crisp_score": 0.7,
        "convenience_score": 0.7,
        "average_price_level": price,
        "daily_recommendation_role": role,
        "nutrition": nutrition,
        "seasons": seasons,
    }
    values.update(changes)
    return RecommendationFruit(**values)


def test_filtering_keeps_out_of_season_but_removes_unavailable_and_supporting() -> None:
    fruits = [
        fruit(1, seasons=(SeasonWindow("全国", 1, 3, 0.9),)),
        fruit(2, seasons=(SeasonWindow("全国", 1, 12, 0.9, supply_status="unavailable"),)),
        fruit(3, role="supporting"),
        fruit(4),
    ]
    eligible = filter_eligible_fruits(fruits, user(), RecommendationContext(month=7))
    assert [item.id for item in eligible] == [1, 4]


def test_unwilling_and_untried_discovery_zero_are_hard_exclusions() -> None:
    fruits = [fruit(1), fruit(2), fruit(3)]
    preferences = {
        1: FruitPreference(willing_to_try=False),
        2: FruitPreference(has_tried=False, willing_to_try=True),
    }
    eligible = filter_eligible_fruits(
        fruits,
        user(discovery_level=0, fruit_preferences=preferences),
        RecommendationContext(month=7),
    )
    assert [item.id for item in eligible] == [3]


def test_normalization_uses_portion_and_preserves_missing_values() -> None:
    first = fruit(1, nutrition=NutritionProfile(energy=10))
    second = fruit(2, nutrition=NutritionProfile(energy=30), default_portion_grams=200)
    normalized = normalize_nutrition_profiles([first, second])
    assert normalized[1].energy == 0.0
    assert normalized[2].energy == 1.0
    assert normalized[1].vitamin_c is None


def test_price_penalty_is_one_sided() -> None:
    results = score_candidates(
        [fruit(1, price=1), fruit(2, price=3)],
        user(price_level=1),
        RecommendationContext(month=7),
    )
    by_id = {item.fruit.id: item for item in results}
    assert by_id[1].scores.price_match_score == 1
    assert by_id[2].scores.price_match_score == 0


def test_history_and_feedback_use_time_decay() -> None:
    today = date(2026, 8, 1)
    recent = HistoryEvent(1, today, times_shown=1)
    old = HistoryEvent(2, today - timedelta(days=60), times_shown=1)
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    events = (
        FeedbackEvent(1, "disliked", now),
        FeedbackEvent(2, "disliked", now - timedelta(days=180)),
    )
    results = score_candidates(
        [fruit(1), fruit(2)],
        user(),
        RecommendationContext(
            month=8,
            today=today,
            history_events=(recent, old),
            feedback_events=events,
        ),
    )
    by_id = {item.fruit.id: item for item in results}
    assert by_id[1].scores.history_diversity_score < by_id[2].scores.history_diversity_score
    assert by_id[1].scores.feedback_adjustment < by_id[2].scores.feedback_adjustment


def test_pair_search_uses_complement_and_excludes_previous_pair() -> None:
    fruits = [
        fruit(1, category="citrus", nutrition=NutritionProfile(1, 0, 1, 0, 1, 0)),
        fruit(2, category="berry", nutrition=NutritionProfile(0, 1, 0, 1, 0, 1)),
        fruit(3, category="stone", nutrition=NutritionProfile(0.9, 0, 0.9, 0, 0.9, 0)),
    ]
    context = RecommendationContext(
        month=7,
        random_seed=42,
        previous_pairs=(frozenset({1, 2}),),
        excluded_pair=frozenset({1, 2}),
    )
    selection = select_recommendation_pair(fruits, user(), context)
    assert {selection.first.fruit.id, selection.second.fruit.id} != {1, 2}
    assert selection.pair_score > 0


def test_full_result_and_reasons_are_reproducible_with_seed() -> None:
    fruits = [fruit(index, category=str(index)) for index in range(1, 6)]
    context = RecommendationContext(month=7, random_seed=20260801)
    first = recommend_fruits(fruits, user(), context)
    second = recommend_fruits(list(reversed(fruits)), user(), context)
    assert [item.fruit.id for item in first.items] == [item.fruit.id for item in second.items]
    assert [
        [reason.model_dump() for reason in item.reasons]
        for item in first.items
    ] == [
        [reason.model_dump() for reason in item.reasons]
        for item in second.items
    ]
    assert all(reason.contribution >= 0 for item in first.items for reason in item.reasons)


def test_taste_match_averages_only_configured_dimensions() -> None:
    fruits = [
        fruit(1, sweet_score=1.0, sour_score=0.0, soft_score=0.0, crisp_score=0.0),
        fruit(2, sweet_score=0.0, sour_score=1.0, soft_score=1.0, crisp_score=1.0),
    ]
    results = score_candidates(
        fruits,
        user(
            sweet_preference=1.0,
            sour_preference=None,
            soft_preference=None,
            crisp_preference=None,
        ),
        RecommendationContext(month=7),
    )
    by_id = {result.fruit.id: result for result in results}
    assert by_id[1].scores.taste_match > by_id[2].scores.taste_match


def test_future_history_and_unknown_feedback_are_rejected() -> None:
    today = date(2026, 8, 1)
    with pytest.raises(InvalidRecommendationInputError):
        score_candidates(
            [fruit(1), fruit(2)],
            user(),
            RecommendationContext(
                month=8,
                today=today,
                history_events=(HistoryEvent(1, today + timedelta(days=1)),),
            ),
        )
    with pytest.raises(InvalidRecommendationInputError):
        score_candidates(
            [fruit(1), fruit(2)],
            user(),
            RecommendationContext(
                month=8,
                today=today,
                feedback_events=(
                    FeedbackEvent(
                        1,
                        "unknown",
                        datetime(2026, 8, 1, tzinfo=timezone.utc),
                    ),
                ),
            ),
        )


def test_exploration_role_is_lower_for_cold_start_but_favorite_overrides() -> None:
    fruits = [
        fruit(1, role="main"),
        fruit(2, role="exploration"),
    ]
    cold_start = {
        item.fruit.id: item
        for item in score_candidates(
            fruits,
            user(),
            RecommendationContext(month=7),
        )
    }
    assert cold_start[1].base_score > cold_start[2].base_score

    explicit_favorite = {
        item.fruit.id: item
        for item in score_candidates(
            fruits,
            user(fruit_preferences={2: FruitPreference(preference_score=2)}),
            RecommendationContext(month=7),
        )
    }
    assert explicit_favorite[2].scores.explicit_preference == pytest.approx(1.0)
