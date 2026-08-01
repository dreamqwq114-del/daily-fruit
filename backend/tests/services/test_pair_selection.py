from datetime import date, timedelta

import pytest

from app.services import (
    FruitPreference,
    HistoryEvent,
    NoRecommendationCandidatesError,
    NutritionProfile,
    PairSelection,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SeasonWindow,
    nutrition_complement_score,
    score_candidates,
    select_recommendation_pair,
)
from app.services.recommendation_service import _recently_shown_fruit_ids


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


def test_pair_score_uses_v2_pair_formula() -> None:
    fruits = [
        make_fruit(1, profile(0, 0, 0, 0, 0, 0)),
        make_fruit(2, profile(1, 1, 1, 1, 1, 1)),
    ]
    result = select_recommendation_pair(
        fruits,
        make_user(),
        RecommendationContext(month=7),
    )

    expected = (
        0.70 * ((result.first.base_score + result.second.base_score) / 2)
        + 0.15 * result.nutrition_pair_score
        + 0.10 * result.sensory_category_diversity
        + 0.05 * result.pair_novelty
    )
    assert result.pair_score == pytest.approx(expected)
    assert 0 <= result.pair_score <= 1


def _pair_ids(result: PairSelection) -> frozenset[int]:
    """把算法结果折叠成无序 pair，测试不依赖展示 rank。"""

    return frozenset(
        {
            result.first.fruit.id,
            result.second.fruit.id,
        }
    )


def test_pair_from_last_three_days_is_avoided_when_alternative_exists() -> None:
    fruits = [make_fruit(index, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)) for index in range(1, 5)]
    context = RecommendationContext(
        month=7,
        today=date(2026, 8, 10),
        cooldown_pairs=(frozenset({1, 2}),),
    )

    result = select_recommendation_pair(fruits, make_user(), context)

    assert _pair_ids(result) != frozenset({1, 2})


def test_yesterdays_fruits_are_avoided_when_enough_alternatives_exist() -> None:
    today = date(2026, 8, 10)
    fruits = [make_fruit(index, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)) for index in range(1, 5)]
    context = RecommendationContext(
        month=7,
        today=today,
        history_events=(
            HistoryEvent(1, today - timedelta(days=1)),
            HistoryEvent(2, today - timedelta(days=1)),
        ),
    )

    result = select_recommendation_pair(fruits, make_user(), context)

    assert _pair_ids(result) == frozenset({3, 4})


def test_same_day_history_is_not_cross_day_fruit_cooldown() -> None:
    today = date(2026, 8, 10)
    context = RecommendationContext(
        month=7,
        today=today,
        history_events=(
            HistoryEvent(1, today),
            HistoryEvent(2, today - timedelta(days=1)),
            HistoryEvent(3, today - timedelta(days=2)),
        ),
    )

    assert _recently_shown_fruit_ids(context, days=1) == frozenset({2})


def test_single_fruit_cooldown_relaxes_when_it_blocks_all_pairs() -> None:
    today = date(2026, 8, 10)
    fruits = [make_fruit(index, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)) for index in range(1, 4)]
    context = RecommendationContext(
        month=7,
        today=today,
        history_events=tuple(
            HistoryEvent(index, today - timedelta(days=1))
            for index in range(1, 4)
        ),
    )

    result = select_recommendation_pair(fruits, make_user(), context)

    assert len(_pair_ids(result)) == 2


def test_pair_cooldown_relaxes_when_user_has_too_few_candidates() -> None:
    fruits = [make_fruit(index, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)) for index in range(1, 4)]
    all_pairs = tuple(
        frozenset(pair)
        for pair in ((1, 2), (1, 3), (2, 3))
    )
    context = RecommendationContext(month=7, cooldown_pairs=all_pairs)

    result = select_recommendation_pair(fruits, make_user(), context)

    assert _pair_ids(result) in set(all_pairs)


def test_excluded_pair_is_never_restored_during_relaxation() -> None:
    fruits = [make_fruit(index, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)) for index in range(1, 4)]
    all_pairs = tuple(
        frozenset(pair)
        for pair in ((1, 2), (1, 3), (2, 3))
    )
    context = RecommendationContext(
        month=7,
        cooldown_pairs=all_pairs,
        excluded_pair=frozenset({1, 2}),
    )

    result = select_recommendation_pair(fruits, make_user(), context)

    assert _pair_ids(result) != frozenset({1, 2})


def test_refresh_never_returns_excluded_pair() -> None:
    fruits = [
        make_fruit(index, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5))
        for index in range(1, 4)
    ]
    context = RecommendationContext(
        month=7,
        excluded_pair=frozenset({1, 2}),
    )

    result = select_recommendation_pair(fruits, make_user(), context)

    assert _pair_ids(result) != frozenset({1, 2})


def test_refresh_fails_when_only_excluded_pair_is_legal() -> None:
    fruits = [
        make_fruit(1, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)),
        make_fruit(2, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)),
    ]
    context = RecommendationContext(
        month=7,
        excluded_pair=frozenset({1, 2}),
    )

    with pytest.raises(NoRecommendationCandidatesError):
        select_recommendation_pair(fruits, make_user(), context)


def test_old_pair_can_return_after_cooldown_period() -> None:
    fruits = [
        make_fruit(1, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)),
        make_fruit(2, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)),
    ]
    context = RecommendationContext(
        month=7,
        previous_pairs=(frozenset({1, 2}),),
        cooldown_pairs=(),
    )

    result = select_recommendation_pair(fruits, make_user(), context)

    assert _pair_ids(result) == frozenset({1, 2})


def test_same_user_date_and_refresh_seed_remain_deterministic() -> None:
    fruits = [make_fruit(index, profile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)) for index in range(1, 6)]
    context = RecommendationContext(
        month=7,
        today=date(2026, 8, 10),
        random_seed=20260810,
        cooldown_pairs=(frozenset({1, 2}),),
    )

    first = select_recommendation_pair(fruits, make_user(), context)
    second = select_recommendation_pair(list(reversed(fruits)), make_user(), context)

    assert _pair_ids(first) == _pair_ids(second)
