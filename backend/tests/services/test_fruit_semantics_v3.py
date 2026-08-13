import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.services import (
    FruitPreference,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SeasonWindow,
    filter_eligible_fruits,
    is_exploration_recommendation,
    score_candidates,
    select_recommendation_pair,
)
from app.services.recommendation_core.common import NoRecommendationCandidatesError
from app.services.recommendation_core.selection_options import matching_dimensions_for


TEST_HARVEST_EVIDENCE = {
    "data_quality": "high",
    "source_note": "test harvest evidence",
    "source_year": 2026,
    "is_scoring_enabled": True,
}


def make_user(*, discovery_level: int = 1, preferences: dict[int, FruitPreference] | None = None) -> RecommendationUser:
    return RecommendationUser(
        region="华东",
        sweet_preference=0.7,
        sour_preference=0.3,
        soft_preference=0.7,
        crisp_preference=0.3,
        price_level=2,
        convenience_preference=0.5,
        discovery_level=discovery_level,
        fruit_preferences=preferences or {},
    )


def make_fruit(fruit_id: int, *, category: str = "A", role: str = "main") -> RecommendationFruit:
    return RecommendationFruit(
        id=fruit_id,
        name=f"水果{fruit_id}",
        category=category,
        display_group=category,
        taste="演示",
        sweet_score=0.8,
        sour_score=0.2,
        soft_score=0.8,
        crisp_score=0.2,
        convenience_score=0.5,
        average_price_level=2,
        daily_recommendation_role=role,
        seasons=(
            SeasonWindow("全国", 1, 12, 0.9, **TEST_HARVEST_EVIDENCE),
        ),
    )


def test_display_group_does_not_change_score_or_pair() -> None:
    first = make_fruit(1, category="苹果梨类")
    second = make_fruit(2, category="桃樱类")
    user = make_user()
    context = RecommendationContext(month=7, random_seed=42)

    original = select_recommendation_pair([first, second], user, context)
    changed = select_recommendation_pair(
        [
            make_fruit(1, category="热带与特色水果"),
            make_fruit(2, category="苹果梨类"),
        ],
        user,
        context,
    )

    assert original.pair_score == pytest.approx(changed.pair_score)
    assert original.sensory_category_diversity == pytest.approx(
        changed.sensory_category_diversity
    )


def test_discovery_levels_distinguish_unknown_and_explicit_untried() -> None:
    preferences = {
        1: FruitPreference(has_tried=False, willing_to_try=True),
        2: FruitPreference(has_tried=False, willing_to_try=True),
    }
    fruits = [make_fruit(1), make_fruit(2)]
    assert filter_eligible_fruits(
        fruits,
        make_user(discovery_level=0, preferences=preferences),
        RecommendationContext(month=7),
    ) == []

    with pytest.raises(NoRecommendationCandidatesError):
        select_recommendation_pair(
            fruits,
            make_user(discovery_level=1, preferences=preferences),
            RecommendationContext(month=7),
        )

    result = select_recommendation_pair(
        fruits,
        make_user(discovery_level=2, preferences=preferences),
        RecommendationContext(month=7),
    )
    assert {result.first.fruit.id, result.second.fruit.id} == {1, 2}


def test_unknown_has_tried_is_not_marked_as_exploration() -> None:
    fruit = make_fruit(1)
    assert not is_exploration_recommendation(fruit, None, make_user())
    assert is_exploration_recommendation(
        fruit,
        FruitPreference(has_tried=False, willing_to_try=True),
        make_user(discovery_level=1),
    )
    assert not is_exploration_recommendation(
        fruit,
        FruitPreference(has_tried=False, willing_to_try=False),
        make_user(discovery_level=2),
    )


def test_supporting_fruit_is_not_in_default_pair() -> None:
    with pytest.raises(NoRecommendationCandidatesError):
        select_recommendation_pair(
            [make_fruit(1, role="supporting"), make_fruit(2)],
            make_user(),
            RecommendationContext(month=7),
        )


def test_seed_semantics_and_derived_convenience_are_consistent() -> None:
    root = Path(__file__).resolve().parents[3]
    fruits = json.loads((root / "data" / "fruits_seed.json").read_text(encoding="utf-8"))
    assert len(fruits) == 24
    assert {item["daily_recommendation_role"] for item in fruits} == {"main", "supporting"}
    assert sum(item["daily_recommendation_role"] == "supporting" for item in fruits) == 1
    assert {item["novelty_level"] for item in fruits} == {0, 1, 2}
    for item in fruits:
        expected = (
            Decimal("0.30") * Decimal(str(item["portability_score"]))
            + Decimal("0.25") * (1 - Decimal(str(item["preparation_difficulty"])))
            + Decimal("0.25") * (1 - Decimal(str(item["messiness_score"])))
            + Decimal("0.20") * (1 - Decimal(str(item["storage_difficulty"])))
        ).quantize(Decimal("0.001"))
        assert Decimal(str(item["convenience_score"])) == expected


def test_seed_annotations_preserve_required_relative_relationships() -> None:
    root = Path(__file__).resolve().parents[3]
    rows = {
        item["code"]: item
        for item in json.loads(
            (root / "data" / "fruits_seed.json").read_text(encoding="utf-8")
        )
    }
    assert rows["lemon"]["sour_score"] > rows["apple"]["sour_score"]
    assert rows["banana"]["soft_score"] > rows["apple"]["soft_score"]
    assert rows["pear"]["crisp_score"] > rows["banana"]["crisp_score"]
    assert rows["durian"]["aroma_intensity"] > rows["blueberry"]["aroma_intensity"]
    assert rows["pineapple"]["preparation_difficulty"] > rows["banana"]["preparation_difficulty"]
    assert rows["apple"]["portability_score"] > rows["watermelon"]["portability_score"]


def test_selection_option_seed_has_only_the_supported_parent_fruits() -> None:
    root = Path(__file__).resolve().parents[3]
    rows = json.loads(
        (root / "data" / "fruit_selection_options_seed.json").read_text(
            encoding="utf-8"
        )
    )
    by_fruit = {}
    for row in rows:
        by_fruit.setdefault(row["fruit_code"], []).append(row)

    assert set(by_fruit) == {
        "apple",
        "grape",
        "peach",
        "kiwifruit",
        "pomegranate",
        "dragon_fruit",
    }
    assert {row["code"] for row in by_fruit["apple"]} == {
        "crisp",
        "powdery",
    }
    assert {row["code"] for row in by_fruit["grape"]} == {
        "soft_juicy",
        "hard_crisp",
    }
    assert {row["code"] for row in by_fruit["peach"]} == {"crisp", "soft"}
    assert {row["code"] for row in by_fruit["kiwifruit"]} == {
        "green",
        "yellow",
        "red",
    }
    assert {row["code"] for row in by_fruit["dragon_fruit"]} == {"red", "white"}
    expected_defaults = {
        "apple": "crisp",
        "grape": "hard_crisp",
        "peach": "crisp",
        "kiwifruit": "green",
        "pomegranate": "soft_seed",
        "dragon_fruit": "red",
    }
    for fruit_code, fruit_rows in by_fruit.items():
        assert sum(row["is_default"] and row["is_active"] for row in fruit_rows) == 1
        assert all(row["is_active"] for row in fruit_rows)
        assert next(row for row in fruit_rows if row["is_default"])["code"] == expected_defaults[fruit_code]
        if fruit_code in {"apple", "grape", "peach"}:
            assert matching_dimensions_for(
                RecommendationFruit(
                    id=1,
                    code=fruit_code,
                    name=fruit_code,
                    sweet_score=0.5,
                    sour_score=0.5,
                    soft_score=0.5,
                    crisp_score=0.5,
                    convenience_score=0.5,
                    average_price_level=2,
                )
            ) == ("texture_score",)
            assert next(row for row in fruit_rows if row["is_default"]).get("texture_score") is None
            assert min(
                row["texture_score"] for row in fruit_rows if "texture_score" in row
            ) in {0.15, 0.20, 0.25}
            if fruit_code == "grape":
                soft_juicy = next(row for row in fruit_rows if row["code"] == "soft_juicy")
                assert soft_juicy["sweet_score"] == 0.70
                assert soft_juicy["sour_score"] == 0.30
                assert soft_juicy["texture_score"] == 0.20
                assert soft_juicy["ripe_storage_score"] == 0.10
        elif fruit_code == "kiwifruit":
            assert matching_dimensions_for(
                RecommendationFruit(
                    id=1,
                    code="kiwifruit",
                    name="猕猴桃",
                    sweet_score=0.5,
                    sour_score=0.5,
                    soft_score=0.5,
                    crisp_score=0.5,
                    convenience_score=0.5,
                    average_price_level=2,
                )
            ) == ("sweet_score", "sour_score")
            assert "sour_score" not in next(row for row in fruit_rows if row["code"] == "green")
            assert next(row for row in fruit_rows if row["code"] == "yellow")["sour_score"] == 0.4
        elif fruit_code == "pomegranate":
            assert matching_dimensions_for(
                RecommendationFruit(
                    id=1,
                    code="pomegranate",
                    name="石榴",
                    sweet_score=0.68,
                    sour_score=0.42,
                    soft_score=0.25,
                    crisp_score=0.55,
                    convenience_score=0.5,
                    average_price_level=2,
                )
            ) == ()
            hard_seed = next(
                row for row in fruit_rows if row["code"] == "hard_seed"
            )
            assert hard_seed["sweet_score"] == 0.70
            assert hard_seed["sour_score"] == 0.25
            assert hard_seed["convenience_score"] == 0.20
            assert all(
                row.get(field) is None
                for row in fruit_rows
                for field in ("soft_score", "crisp_score", "texture_score")
            )
        else:
            assert matching_dimensions_for(
                RecommendationFruit(
                    id=1,
                    code="dragon_fruit",
                    name="火龙果",
                    sweet_score=0.6,
                    sour_score=0.1,
                    soft_score=0.65,
                    crisp_score=0.35,
                    convenience_score=0.8,
                    average_price_level=2,
                )
            ) == ()
