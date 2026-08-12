from __future__ import annotations

from dataclasses import replace
from typing import get_type_hints

import pytest

import app.services.recommendation_core.selection_options as selection_options_module

from app.services import (
    FruitPreference,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SeasonWindow,
    SelectionOption,
    SelectionOptionPreference,
    score_candidates,
)
from app.services.recommendation_core.selection_options import (
    resolve_selection_option,
)
from app.services.recommendation_core.common import InvalidRecommendationInputError


def make_user(**changes: object) -> RecommendationUser:
    values: dict[str, object] = {
        "region": "华东",
        "sweet_preference": 0.7,
        "sour_preference": 0.3,
        "soft_preference": None,
        "crisp_preference": None,
        "texture_preference": 0.8,
        "price_level": 2,
        "convenience_preference": 0.5,
    }
    values.update(changes)
    return RecommendationUser(**values)


def make_peach() -> RecommendationFruit:
    return RecommendationFruit(
        id=10,
        code="peach",
        name="桃",
        sweet_score=0.7,
        sour_score=0.3,
        soft_score=0.6,
        crisp_score=0.5,
        convenience_score=0.6,
        average_price_level=2,
        texture_score=0.8,
        seasons=(SeasonWindow("全国", 1, 12, 0.9),),
        selection_options=(
            SelectionOption(
                id=101,
                fruit_id=10,
                code="crisp",
                name="脆桃型",
                soft_score=0.2,
                crisp_score=0.9,
                texture_score=0.8,
                is_default=True,
                display_order=1,
            ),
            SelectionOption(
                id=102,
                fruit_id=10,
                code="soft",
                name="软桃型",
                soft_score=0.9,
                crisp_score=0.2,
                texture_score=0.15,
                display_order=2,
            ),
        ),
    )


def make_kiwifruit() -> RecommendationFruit:
    return RecommendationFruit(
        id=11,
        code="kiwifruit",
        name="猕猴桃",
        sweet_score=0.4,
        sour_score=0.6,
        soft_score=0.5,
        crisp_score=0.5,
        convenience_score=0.6,
        average_price_level=2,
        texture_score=0.25,
        seasons=(SeasonWindow("全国", 1, 12, 0.9),),
        selection_options=(
            SelectionOption(
                id=201,
                fruit_id=11,
                code="green",
                name="绿心",
                is_default=True,
                display_order=1,
            ),
            SelectionOption(
                id=202,
                fruit_id=11,
                code="yellow",
                name="黄心",
                sweet_score=0.6,
                sour_score=0.4,
                display_order=2,
            ),
            SelectionOption(
                id=203,
                fruit_id=11,
                code="red",
                name="红心",
                sweet_score=0.65,
                sour_score=0.3,
                display_order=3,
            ),
        ),
    )


def make_dragon_fruit() -> RecommendationFruit:
    return RecommendationFruit(
        id=40,
        code="dragon_fruit",
        name="火龙果",
        sweet_score=0.55,
        sour_score=0.18,
        soft_score=0.72,
        crisp_score=0.28,
        texture_score=0.28,
        convenience_score=0.8,
        average_price_level=2,
        seasons=(SeasonWindow("全国", 1, 12, 0.9),),
        selection_options=(
            SelectionOption(
                id=401,
                fruit_id=40,
                code="red",
                name="红心",
                is_default=True,
                display_order=1,
            ),
            SelectionOption(
                id=402,
                fruit_id=40,
                code="white",
                name="白心",
                sweet_score=0.50,
                sour_score=0.05,
                texture_score=0.40,
                display_order=2,
            ),
        ),
    )


def test_selection_option_public_exports_and_annotations_resolve() -> None:
    assert selection_options_module.MATCHING_DIMENSIONS["apple"] == (
        "texture_score",
    )
    assert get_type_hints(
        selection_options_module._option_preferences_for
    )["preferences"]


def test_dragon_fruit_explicit_white_selection_overrides_score_profile() -> None:
    fruit = make_dragon_fruit()
    resolved = resolve_selection_option(
        fruit,
        fruit.selection_options,
        None,
        (SelectionOptionPreference(1, 40, 402, "liked"),),
        make_user(),
    )

    assert resolved is not None
    assert resolved.resolution_source == "explicit"
    assert resolved.resolved_option_code == "white"
    assert resolved.effective_sour_score == pytest.approx(0.05)
    assert resolved.effective_texture_score == pytest.approx(0.40)


def make_pomegranate() -> RecommendationFruit:
    return RecommendationFruit(
        id=30,
        code="pomegranate",
        name="石榴",
        sweet_score=0.68,
        sour_score=0.42,
        soft_score=0.25,
        crisp_score=0.55,
        convenience_score=0.6,
        average_price_level=2,
        texture_score=0.35,
        seasons=(SeasonWindow("全国", 1, 12, 0.9),),
        selection_options=(
            SelectionOption(
                id=301,
                fruit_id=30,
                code="soft_seed",
                name="软籽型",
                is_default=True,
                display_order=1,
            ),
            SelectionOption(
                id=302,
                fruit_id=30,
                code="hard_seed",
                name="硬籽型",
                sweet_score=0.70,
                sour_score=0.25,
                convenience_score=0.20,
                display_order=2,
            ),
        ),
    )


def test_global_soft_and_crisp_preferences_resolve_a_real_peach_option() -> None:
    peach = make_peach()
    crisp_user = make_user(texture_preference=0.9)
    soft_user = make_user(texture_preference=0.1)

    crisp = resolve_selection_option(peach, peach.selection_options, None, (), crisp_user)
    soft = resolve_selection_option(peach, peach.selection_options, None, (), soft_user)

    assert crisp is not None and crisp.resolved_option_code == "crisp"
    assert soft is not None and soft.resolved_option_code == "soft"
    assert crisp.effective_soft_score == pytest.approx(0.2)
    assert soft.effective_soft_score == pytest.approx(0.85)


def test_liked_option_wins_over_unknown_and_parent_dislike_can_have_exception() -> None:
    peach = make_peach()
    user = make_user()
    parent = FruitPreference(preference_score=-1)
    resolved = resolve_selection_option(
        peach,
        peach.selection_options,
        parent,
        (SelectionOptionPreference(1, 10, 102, "liked"),),
        user,
    )

    assert resolved is not None
    assert resolved.resolved_option_code == "soft"
    assert resolved.resolution_source == "explicit"
    assert resolved.effective_explicit_preference == 1.0
    assert resolved.option_explicitly_liked is True


def test_disliked_default_is_never_a_fallback_and_all_disliked_excludes_parent() -> None:
    peach = make_peach()
    user = make_user()
    soft_only = resolve_selection_option(
        peach,
        peach.selection_options,
        None,
        (SelectionOptionPreference(1, 10, 101, "disliked"),),
        user,
    )
    assert soft_only is not None and soft_only.resolved_option_code == "soft"

    none_allowed = resolve_selection_option(
        peach,
        peach.selection_options,
        None,
        (
            SelectionOptionPreference(1, 10, 101, "disliked"),
            SelectionOptionPreference(1, 10, 102, "disliked"),
        ),
        user,
    )
    assert none_allowed is None


def test_option_preferences_cannot_cross_contaminate_parent() -> None:
    with pytest.raises(InvalidRecommendationInputError):
        resolve_selection_option(
            make_peach(),
            make_peach().selection_options,
            None,
            (SelectionOptionPreference(1, 11, 101, "liked"),),
            make_user(),
        )


def test_parent_is_scored_once_and_option_is_not_a_second_top_level_fruit() -> None:
    peach = make_peach()
    scored = score_candidates(
        [peach, replace(peach, id=12, code="apple", name="苹果", selection_options=())],
        make_user(),
        RecommendationContext(month=7),
    )

    assert [item.fruit.id for item in scored] == [10, 12]
    assert len([item for item in scored if item.fruit.id == 10]) == 1
    peach_score = next(item for item in scored if item.fruit.id == 10)
    assert peach_score.resolved_candidate is not None
    # The score uses the selected real option; it is never an averaged profile.
    assert peach_score.resolved_candidate.resolved_option_code == "crisp"
    assert peach_score.resolved_candidate.effective_crisp_score == 0.8


def test_adding_late_near_duplicate_option_does_not_change_resolution() -> None:
    peach = make_peach()
    baseline = resolve_selection_option(
        peach,
        peach.selection_options,
        None,
        (),
        make_user(texture_preference=0.9),
    )
    duplicate = SelectionOption(
        id=199,
        fruit_id=10,
        code="crisp-copy",
        name="脆桃型（重复演示）",
        soft_score=0.2,
        crisp_score=0.9,
        texture_score=0.8,
        display_order=99,
    )
    changed = resolve_selection_option(
        peach,
        (*peach.selection_options, duplicate),
        None,
        (),
        make_user(texture_preference=0.9),
    )

    assert baseline is not None and changed is not None
    assert changed.resolved_option_id == baseline.resolved_option_id
    assert changed.effective_crisp_score == baseline.effective_crisp_score


def test_kiwifruit_explicit_green_preference_excludes_unknown_siblings() -> None:
    fruit = make_kiwifruit()
    resolved = resolve_selection_option(
        fruit,
        fruit.selection_options,
        None,
        (
            SelectionOptionPreference(1, 11, 201, "liked"),
            SelectionOptionPreference(1, 11, 202, "disliked"),
            SelectionOptionPreference(1, 11, 203, "disliked"),
        ),
        make_user(sweet_preference=0.95, sour_preference=0.05),
    )

    assert resolved is not None
    assert resolved.resolved_option_code == "green"
    assert resolved.acceptable_option_ids == ()
    assert resolved.avoided_option_ids == (202, 203)


def test_kiwifruit_inference_uses_the_shared_normalized_taste_weights() -> None:
    fruit = make_kiwifruit()
    resolved = resolve_selection_option(
        fruit,
        fruit.selection_options,
        None,
        (),
        make_user(
            sweet_preference=0.10,
            sour_preference=0.10,
            texture_preference=None,
        ),
    )

    # Equal weighting chooses red for this profile. The shared 0.40/0.25
    # sweet/sour weights correctly choose the green parent profile.
    assert resolved is not None
    assert resolved.resolved_option_code == "green"


def test_pomegranate_without_type_preference_keeps_parent_scores_and_no_selection() -> None:
    fruit = make_pomegranate()
    resolved = resolve_selection_option(
        fruit,
        fruit.selection_options,
        None,
        (),
        make_user(texture_preference=0.05),
    )

    assert resolved is not None
    assert resolved.resolved_option_id is None
    assert resolved.resolution_source == "not_applicable"
    assert (
        resolved.effective_sweet_score,
        resolved.effective_sour_score,
        resolved.effective_soft_score,
        resolved.effective_crisp_score,
    ) == (fruit.sweet_score, fruit.sour_score, 0.65, 0.35)


def test_pomegranate_explicit_like_and_avoid_filter_without_score_override() -> None:
    fruit = make_pomegranate()
    liked = resolve_selection_option(
        fruit,
        fruit.selection_options,
        None,
        (SelectionOptionPreference(1, 30, 301, "liked"),),
        make_user(),
    )
    avoided = resolve_selection_option(
        fruit,
        fruit.selection_options,
        None,
        (SelectionOptionPreference(1, 30, 302, "disliked"),),
        make_user(),
    )

    assert liked is not None and liked.resolved_option_code == "soft_seed"
    assert avoided is not None and avoided.resolved_option_code == "soft_seed"
    assert avoided.avoided_option_ids == (302,)
    for resolved in (liked, avoided):
        assert (
            resolved.effective_sweet_score,
            resolved.effective_sour_score,
            resolved.effective_soft_score,
            resolved.effective_crisp_score,
        ) == (0.68, 0.42, 0.65, 0.35)
        assert resolved.effective_convenience_score == fruit.convenience_score


def test_pomegranate_all_types_disliked_is_filtered() -> None:
    fruit = make_pomegranate()
    resolved = resolve_selection_option(
        fruit,
        fruit.selection_options,
        None,
        (
            SelectionOptionPreference(1, 30, 301, "disliked"),
            SelectionOptionPreference(1, 30, 302, "disliked"),
        ),
        make_user(),
    )

    assert resolved is None
