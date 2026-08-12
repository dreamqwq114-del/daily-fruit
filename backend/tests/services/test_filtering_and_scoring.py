import pytest

from app.services import (
    FruitPreference,
    InvalidRecommendationInputError,
    NoRecommendationCandidatesError,
    NutritionProfile,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SeasonWindow,
    filter_eligible_fruits,
    score_candidates,
)


def make_user(**changes: object) -> RecommendationUser:
    values: dict[str, object] = {
        "region": "华东",
        "sweet_preference": 0.8,
        "sour_preference": 0.3,
        "soft_preference": 0.4,
        "crisp_preference": 0.8,
        "price_level": 2,
        "convenience_preference": 0.8,
    }
    values.update(changes)
    return RecommendationUser(**values)


def make_fruit(fruit_id: int, **changes: object) -> RecommendationFruit:
    values: dict[str, object] = {
        "id": fruit_id,
        "name": f"水果{fruit_id}",
        "sweet_score": 0.7,
        "sour_score": 0.3,
        "soft_score": 0.4,
        "crisp_score": 0.8,
        "convenience_score": 0.8,
        "average_price_level": 2,
        "nutrition": NutritionProfile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
        "seasons": (SeasonWindow("全国", 1, 12, 0.8),),
    }
    values.update(changes)
    return RecommendationFruit(**values)


def score_by_id(
    fruits: list[RecommendationFruit],
    user: RecommendationUser | None = None,
    context: RecommendationContext | None = None,
):
    return {
        item.fruit.id: item
        for item in score_candidates(
            fruits,
            user or make_user(),
            context or RecommendationContext(month=7),
        )
    }


def test_forbidden_inactive_and_explicitly_disliked_fruits_are_filtered() -> None:
    fruits = [
        make_fruit(1),
        make_fruit(2, is_active=False),
        make_fruit(3),
        make_fruit(4),
    ]
    user = make_user(
        fruit_preferences={
            1: FruitPreference(is_forbidden=True),
            3: FruitPreference(preference_score=-1),
        }
    )

    assert [
        fruit.id
        for fruit in filter_eligible_fruits(
            fruits,
            user,
            RecommendationContext(month=7),
        )
    ] == [4]


def test_dislike_can_be_scored_when_strict_exclusion_is_disabled() -> None:
    fruits = [make_fruit(1), make_fruit(2)]
    user = make_user(
        fruit_preferences={1: FruitPreference(preference_score=-1)}
    )

    eligible = filter_eligible_fruits(
        fruits,
        user,
        RecommendationContext(month=7, exclude_disliked=False),
    )

    assert [fruit.id for fruit in eligible] == [1, 2]


@pytest.mark.parametrize("score", [-0.99, -0.5, 0.5, 1.5])
def test_non_discrete_preference_score_is_rejected_before_scoring(score: float) -> None:
    fruits = [make_fruit(1), make_fruit(2)]
    invalid_user = make_user(
        fruit_preferences={1: FruitPreference(preference_score=score)}
    )

    with pytest.raises(InvalidRecommendationInputError, match="-1、0、1 或 2"):
        score_candidates(fruits, invalid_user, RecommendationContext(month=7))


@pytest.mark.parametrize("has_tried", [None, True])
@pytest.mark.parametrize("willing_to_try", [False, True])
def test_willingness_without_explicit_untried_state_is_rejected(
    has_tried: bool | None,
    willing_to_try: bool,
) -> None:
    fruits = [make_fruit(1), make_fruit(2)]
    invalid_user = make_user(
        fruit_preferences={
            1: FruitPreference(
                has_tried=has_tried,
                willing_to_try=willing_to_try,
            )
        }
    )

    with pytest.raises(InvalidRecommendationInputError, match="尝试意愿"):
        score_candidates(fruits, invalid_user, RecommendationContext(month=7))


def test_known_out_of_season_is_kept_with_a_score_penalty() -> None:
    fruits = [
        make_fruit(1, seasons=(SeasonWindow("全国", 1, 3, 0.9),)),
        make_fruit(
            2,
            seasons=(SeasonWindow("华南", 1, 12, 0.9, region_level="area"),),
        ),
        make_fruit(3),
    ]

    eligible = filter_eligible_fruits(
        fruits,
        make_user(),
        RecommendationContext(month=7),
    )

    assert [fruit.id for fruit in eligible] == [1, 2, 3]
    scores = score_by_id(eligible)
    assert scores[1].scores.season_score == pytest.approx(0.0)
    assert scores[2].scores.season_score == pytest.approx(0.35)


def test_fewer_than_two_candidates_has_understandable_error() -> None:
    with pytest.raises(NoRecommendationCandidatesError, match="不足两种"):
        score_candidates(
            [make_fruit(1, is_active=False), make_fruit(2)],
            make_user(),
            RecommendationContext(month=7),
        )


def test_each_subscore_and_total_are_normalized() -> None:
    results = score_candidates(
        [make_fruit(1), make_fruit(2)],
        make_user(),
        RecommendationContext(month=7),
    )

    for result in results:
        assert 0 <= result.base_score <= 1
        for field_name in (
            "availability_and_season",
            "explicit_preference",
            "history_diversity_score",
            "convenience_score",
            "price_match_score",
            "taste_match",
        ):
            assert 0 <= getattr(result.scores, field_name) <= 1


def test_base_score_uses_approved_weight_formula() -> None:
    result = score_candidates(
        [make_fruit(1), make_fruit(2)],
        make_user(),
        RecommendationContext(month=7),
    )[0]
    scores = result.scores
    expected = (
        scores.explicit_preference * 0.30
        + scores.taste_match * 0.25
        + scores.availability_and_season * 0.20
        + scores.price_match_score * 0.10
        + scores.convenience_score * 0.10
        + scores.history_diversity_score * 0.05
        + scores.feedback_adjustment
    )

    assert result.base_score == pytest.approx(expected)


def test_in_season_fruit_scores_higher_when_other_factors_match() -> None:
    scores = score_by_id(
        [
            make_fruit(1, seasons=(SeasonWindow("全国", 1, 12, 1.0),)),
            make_fruit(
                2,
                seasons=(SeasonWindow("华南", 1, 12, 1.0, region_level="area"),),
            ),
        ]
    )

    assert scores[1].base_score > scores[2].base_score


def test_liked_fruit_scores_higher_when_other_factors_match() -> None:
    scores = score_by_id(
        [make_fruit(1), make_fruit(2)],
        make_user(
            fruit_preferences={1: FruitPreference(preference_score=2)}
        ),
    )

    assert scores[1].base_score > scores[2].base_score


def test_recent_fruit_scores_lower_when_other_factors_match() -> None:
    scores = score_by_id(
        [make_fruit(1), make_fruit(2)],
        context=RecommendationContext(month=7, recent_fruit_ids=(1,)),
    )

    assert scores[1].scores.history_diversity_score == 0
    assert scores[1].base_score < scores[2].base_score


def test_price_mismatch_scores_lower_when_other_factors_match() -> None:
    scores = score_by_id(
        [
            make_fruit(1, average_price_level=1),
            make_fruit(2, average_price_level=3),
        ],
        make_user(price_level=1),
    )

    assert scores[1].scores.price_match_score == 1
    assert scores[2].scores.price_match_score == 0
    assert scores[1].base_score > scores[2].base_score


def test_feedback_adjusts_preference_and_is_bounded() -> None:
    fruits = [make_fruit(1), make_fruit(2)]
    positive = score_by_id(
        fruits,
        context=RecommendationContext(
            month=7,
            feedback_by_fruit={1: ("liked", "liked", "liked")},
        ),
    )
    negative = score_by_id(
        fruits,
        context=RecommendationContext(
            month=7,
            feedback_by_fruit={1: ("disliked", "tired_of_it")},
        ),
    )

    assert positive[1].scores.feedback_adjustment == pytest.approx(0.15)
    assert negative[1].scores.feedback_adjustment == pytest.approx(-0.15)
    assert negative[1].base_score < negative[2].base_score


def test_input_order_does_not_change_deterministic_score_order() -> None:
    first = make_fruit(1)
    second = make_fruit(2)

    forward = score_candidates(
        [first, second], make_user(), RecommendationContext(month=7)
    )
    reverse = score_candidates(
        [second, first], make_user(), RecommendationContext(month=7)
    )

    assert [item.fruit.id for item in forward] == [1, 2]
    assert [item.fruit.id for item in reverse] == [1, 2]
