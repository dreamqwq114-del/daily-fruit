import pytest

from app.services import (
    FruitPreference,
    NutritionProfile,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SeasonWindow,
    nutrition_complement_score,
    score_candidates,
    select_recommendation_pair,
)


def make_user(**changes: object) -> RecommendationUser:
    values: dict[str, object] = {
        "region": "华东",
        "sweet_preference": 0.5,
        "sour_preference": 0.5,
        "soft_preference": 0.5,
        "crisp_preference": 0.5,
        "price_level": 2,
        "convenience_preference": 0.5,
    }
    values.update(changes)
    return RecommendationUser(**values)


def make_fruit(
    fruit_id: int,
    nutrition: NutritionProfile,
    *,
    season_score: float = 0.9,
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
        seasons=(SeasonWindow("全国", 1, 12, season_score),),
    )


def profile(*values: float) -> NutritionProfile:
    return NutritionProfile(*values)


def test_complement_rewards_covering_first_fruits_low_dimensions() -> None:
    first = profile(1, 0, 1, 0, 1, 0)
    similar = profile(1, 0.1, 0.9, 0.1, 0.9, 0.1)
    complementary = profile(0, 1, 0, 1, 0, 1)

    assert nutrition_complement_score(
        first, complementary
    ) > nutrition_complement_score(first, similar)


def test_second_fruit_is_not_simply_base_score_runner_up() -> None:
    first = make_fruit(1, profile(0.5, 1, 0, 1, 0, 1), season_score=1.0)
    similar = make_fruit(
        2,
        profile(0.5, 0.9, 0.1, 0.9, 0.1, 0.9),
        season_score=0.95,
    )
    complementary = make_fruit(
        3,
        profile(0.5, 0, 1, 0, 1, 0),
        season_score=0.90,
    )
    user = make_user(
        fruit_preferences={1: FruitPreference(preference_score=2)}
    )
    context = RecommendationContext(month=7)

    base_order = [
        item.fruit.id
        for item in score_candidates(
            [first, similar, complementary], user, context
        )
    ]
    result = select_recommendation_pair(
        [first, similar, complementary], user, context
    )

    assert base_order == [1, 2, 3]
    assert result.first.fruit.id == 1
    assert result.second.fruit.id == 3
    assert result.complement_score > 0.8


def test_selected_pair_always_contains_distinct_fruits() -> None:
    fruits = [
        make_fruit(1, profile(0, 0, 0, 0, 0, 0)),
        make_fruit(2, profile(1, 1, 1, 1, 1, 1)),
    ]

    result = select_recommendation_pair(
        fruits,
        make_user(),
        RecommendationContext(month=7),
    )

    assert result.first.fruit.id != result.second.fruit.id


def test_same_random_seed_reproduces_pair() -> None:
    neutral = profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
    fruits = [make_fruit(index, neutral) for index in range(1, 6)]
    context = RecommendationContext(month=7, random_seed=20260731)

    first_run = select_recommendation_pair(fruits, make_user(), context)
    second_run = select_recommendation_pair(
        list(reversed(fruits)), make_user(), context
    )

    assert (
        first_run.first.fruit.id,
        first_run.second.fruit.id,
    ) == (
        second_run.first.fruit.id,
        second_run.second.fruit.id,
    )


def test_random_choice_never_leaves_near_top_window() -> None:
    neutral = profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
    top = make_fruit(1, neutral, season_score=1.0)
    near = make_fruit(2, neutral, season_score=0.96)
    far = make_fruit(3, neutral, season_score=0.80)

    selected_ids = {
        select_recommendation_pair(
            [top, near, far],
            make_user(),
            RecommendationContext(month=7, random_seed=seed),
        ).first.fruit.id
        for seed in range(20)
    }

    assert selected_ids <= {1, 2}
    assert 3 not in selected_ids


def test_second_score_uses_approved_formula() -> None:
    fruits = [
        make_fruit(1, profile(0, 0, 0, 0, 0, 0)),
        make_fruit(2, profile(1, 1, 1, 1, 1, 1)),
    ]
    result = select_recommendation_pair(
        fruits,
        make_user(),
        RecommendationContext(month=7),
    )

    assert result.second_score == pytest.approx(
        result.second.base_score * 0.7 + result.complement_score * 0.3
    )
    assert 0 <= result.second_score <= 1
