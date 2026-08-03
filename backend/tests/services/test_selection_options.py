from __future__ import annotations

from dataclasses import replace

import pytest

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
        "soft_preference": 0.2,
        "crisp_preference": 0.8,
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
        seasons=(SeasonWindow("全国", 1, 12, 0.9),),
        selection_options=(
            SelectionOption(
                id=101,
                fruit_id=10,
                code="crisp",
                name="脆桃型",
                soft_score=0.2,
                crisp_score=0.9,
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
                display_order=2,
            ),
        ),
    )


def make_kiwifruit() -> RecommendationFruit:
    return RecommendationFruit(
        id=11,
        code="kiwifruit",
        name="猕猴桃",
        sweet_score=0.7,
        sour_score=0.4,
        soft_score=0.5,
        crisp_score=0.5,
        convenience_score=0.6,
        average_price_level=2,
        seasons=(SeasonWindow("全国", 1, 12, 0.9),),
        selection_options=(
            SelectionOption(
                id=201,
                fruit_id=11,
                code="green",
                name="绿心",
                sweet_score=0.55,
                sour_score=0.85,
                is_default=True,
                display_order=1,
            ),
            SelectionOption(
                id=202,
                fruit_id=11,
                code="yellow",
                name="黄心",
                sweet_score=0.8,
                sour_score=0.35,
                display_order=2,
            ),
            SelectionOption(
                id=203,
                fruit_id=11,
                code="red",
                name="红心",
                sweet_score=0.85,
                sour_score=0.45,
                display_order=3,
            ),
        ),
    )


def test_global_soft_and_crisp_preferences_resolve_a_real_peach_option() -> None:
    peach = make_peach()
    crisp_user = make_user(soft_preference=0.1, crisp_preference=0.9)
    soft_user = make_user(soft_preference=0.9, crisp_preference=0.1)

    crisp = resolve_selection_option(peach, peach.selection_options, None, (), crisp_user)
    soft = resolve_selection_option(peach, peach.selection_options, None, (), soft_user)

    assert crisp is not None and crisp.resolved_option_code == "crisp"
    assert soft is not None and soft.resolved_option_code == "soft"
    assert crisp.effective_soft_score == 0.2
    assert soft.effective_soft_score == 0.9


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
    assert peach_score.resolved_candidate.effective_crisp_score == 0.9


def test_adding_late_near_duplicate_option_does_not_change_resolution() -> None:
    peach = make_peach()
    baseline = resolve_selection_option(
        peach,
        peach.selection_options,
        None,
        (),
        make_user(soft_preference=0.1, crisp_preference=0.9),
    )
    duplicate = SelectionOption(
        id=199,
        fruit_id=10,
        code="crisp-copy",
        name="脆桃型（重复演示）",
        soft_score=0.2,
        crisp_score=0.9,
        display_order=99,
    )
    changed = resolve_selection_option(
        peach,
        (*peach.selection_options, duplicate),
        None,
        (),
        make_user(soft_preference=0.1, crisp_preference=0.9),
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
