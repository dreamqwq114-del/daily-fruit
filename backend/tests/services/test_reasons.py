import json

from app.services import (
    NutritionProfile,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SeasonWindow,
    recommend_fruits,
)


def make_user() -> RecommendationUser:
    return RecommendationUser(
        region="华东",
        sweet_preference=0.8,
        sour_preference=0.2,
        soft_preference=0.3,
        crisp_preference=0.8,
        price_level=2,
        convenience_preference=0.8,
    )


def make_fruit(
    fruit_id: int,
    nutrition: NutritionProfile,
    *,
    seasons: tuple[SeasonWindow, ...] | None = None,
) -> RecommendationFruit:
    return RecommendationFruit(
        id=fruit_id,
        name=f"水果{fruit_id}",
        sweet_score=0.8,
        sour_score=0.2,
        soft_score=0.3,
        crisp_score=0.8,
        convenience_score=0.8,
        average_price_level=2,
        nutrition=nutrition,
        seasons=(SeasonWindow("全国", 1, 12, 0.9),)
        if seasons is None
        else seasons,
    )


def sample_fruits() -> list[RecommendationFruit]:
    return [
        make_fruit(1, NutritionProfile(0.5, 1, 0, 1, 0, 1)),
        make_fruit(2, NutritionProfile(0.5, 0, 1, 0, 1, 0)),
        make_fruit(3, NutritionProfile(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)),
    ]


def test_result_contains_two_ranked_distinct_items_and_normalized_total() -> None:
    result = recommend_fruits(
        sample_fruits(),
        make_user(),
        RecommendationContext(month=7),
    )

    assert [item.rank for item in result.items] == [1, 2]
    assert len({item.fruit.id for item in result.items}) == 2
    assert result.items[0].pair_score is not None
    assert result.items[1].pair_score is not None
    assert result.total_score == result.items[0].pair_score
    assert 0 <= result.total_score <= 1


def test_each_item_has_two_to_four_stable_structured_reasons() -> None:
    result = recommend_fruits(
        sample_fruits(),
        make_user(),
        RecommendationContext(month=7),
    )

    for item in result.items:
        assert 2 <= len(item.reasons) <= 4
        for reason in item.reasons:
            payload = json.loads(reason.model_dump_json())
            assert list(payload) == ["code", "message", "component", "contribution"]


def test_in_season_reason_only_appears_for_actual_in_season_data() -> None:
    fruits = sample_fruits()
    fruits[0] = make_fruit(
        1,
        fruits[0].nutrition,
        seasons=(SeasonWindow("华南", 1, 12, 1.0, region_level="area"),),
    )
    result = recommend_fruits(
        fruits,
        make_user(),
        RecommendationContext(month=7),
    )

    for item in result.items:
        reason_codes = {reason.code for reason in item.reasons}
        if item.fruit.id == 1:
            assert "availability" not in reason_codes
        else:
            assert "availability" in reason_codes


def test_recent_fruit_does_not_claim_it_was_not_recently_recommended() -> None:
    result = recommend_fruits(
        sample_fruits(),
        make_user(),
        RecommendationContext(month=7, recent_fruit_ids=(1, 2, 3)),
    )

    for item in result.items:
        if item.fruit.id in {1, 2, 3}:
            assert "not_recently_recommended" not in {
                reason.code for reason in item.reasons
            }


def test_positive_feedback_reason_matches_actual_adjustment() -> None:
    result = recommend_fruits(
        sample_fruits(),
        make_user(),
        RecommendationContext(
            month=7,
            feedback_by_fruit={1: ("liked",)},
        ),
    )
    liked_item = next(item for item in result.items if item.fruit.id == 1)

    assert any(
        reason.code == "feedback_match"
        and reason.component == "feedback_adjustment"
        for reason in liked_item.reasons
    )


def test_second_item_explains_strong_nutrition_complement() -> None:
    result = recommend_fruits(
        sample_fruits(),
        make_user(),
        RecommendationContext(month=7),
    )
    second = result.items[1]

    assert second.complement_score is not None
    assert second.complement_score >= 0.4
    assert any(
        reason.code == "nutrition_complement"
        and reason.component == "complement_score"
        for reason in second.reasons
    )


def test_reasons_do_not_contain_medical_or_treatment_promises() -> None:
    result = recommend_fruits(
        sample_fruits(),
        make_user(),
        RecommendationContext(month=7),
    )
    forbidden_phrases = ("治疗", "诊断", "替代药物", "保证改善", "你缺乏")

    messages = [
        reason.message
        for item in result.items
        for reason in item.reasons
    ]
    assert all(
        phrase not in message
        for phrase in forbidden_phrases
        for message in messages
    )


def test_full_result_is_reproducible_with_same_seed() -> None:
    context = RecommendationContext(month=7, random_seed=42)

    first = recommend_fruits(sample_fruits(), make_user(), context)
    second = recommend_fruits(
        list(reversed(sample_fruits())), make_user(), context
    )

    assert [item.fruit.id for item in first.items] == [
        item.fruit.id for item in second.items
    ]
    assert [
        [reason.model_dump() for reason in item.reasons]
        for item in first.items
    ] == [
        [reason.model_dump() for reason in item.reasons]
        for item in second.items
    ]
