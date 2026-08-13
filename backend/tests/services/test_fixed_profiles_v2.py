import csv
import json
from datetime import date
from pathlib import Path

from app.seed.seed_fruits import load_seed_dataset
from app.services import (
    FruitPreference,
    HistoryEvent,
    NutritionProfile,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SelectionOption,
    SeasonWindow,
    recommend_fruits,
    score_candidates,
)


ROOT = Path(__file__).resolve().parents[3]
SEVEN_PROFILES = (
    "low_budget",
    "sour_sweet",
    "sweet_soft",
    "mango_forbidden",
    "recently_ate_mango",
    "untried_avocado_durian",
    "cold_start",
)


def load_seed_fruits() -> list[RecommendationFruit]:
    rows = json.loads((ROOT / "data" / "fruits_seed.json").read_text(encoding="utf-8"))
    option_rows = json.loads(
        (ROOT / "data" / "fruit_selection_options_seed.json").read_text(
            encoding="utf-8"
        )
    )
    options_by_code: dict[str, list[SelectionOption]] = {}
    fruit_ids_by_code = {
        row["code"]: fruit_id for fruit_id, row in enumerate(rows, start=1)
    }
    for option_id, option in enumerate(option_rows, start=1):
        fruit_code = option["fruit_code"]
        options_by_code.setdefault(fruit_code, []).append(
            SelectionOption(
                id=option_id,
                fruit_id=fruit_ids_by_code[fruit_code],
                code=option["code"],
                name=option["name"],
                sweet_score=option.get("sweet_score"),
                sour_score=option.get("sour_score"),
                texture_score=option.get("texture_score"),
                ripe_storage_score=option.get("ripe_storage_score"),
                convenience_score=option.get("convenience_score"),
                is_default=option["is_default"],
                is_active=option["is_active"],
                display_order=option["display_order"],
                data_quality=option["data_quality"],
                data_source_note=option.get("data_source_note"),
            )
        )
    profiles = {
        row["code"]: row
        for row in json.loads(
            (ROOT / "data" / "fruit_profile_seed.json").read_text(encoding="utf-8")
        )
    }
    nutrition = {
        row["fruit_name"]: row
        for row in csv.DictReader(
            (ROOT / "data" / "nutrition_demo.csv").open(
                encoding="utf-8-sig", newline=""
            )
        )
    }
    seasons: dict[str, list[SeasonWindow]] = {row["name"]: [] for row in rows}
    for row in load_seed_dataset().seasons:
        seasons[row.fruit_name].append(
            SeasonWindow(
                region=row.region,
                region_level=row.region_level,
                start_month=row.start_month,
                end_month=row.end_month,
                season_score=float(row.season_score),
                availability_score=float(row.availability_score),
                supply_status=row.supply_status,
                data_scope=row.data_scope,
                data_quality=row.data_quality,
                source_note=row.source_note,
                source_year=row.source_year,
                is_scoring_enabled=row.is_scoring_enabled,
            )
        )
    result = []
    for fruit_id, row in enumerate(rows, start=1):
        profile = profiles[row["code"]]
        values = nutrition[row["name"]]
        result.append(
            RecommendationFruit(
                id=fruit_id,
                name=row["name"],
                code=row["code"],
                aliases=tuple(row["aliases"]),
                category=row["category"],
                taste=row["taste"],
                sweet_score=profile["sweet_score"],
                sour_score=profile["sour_score"],
                soft_score=1 - profile["texture_score"],
                crisp_score=profile["texture_score"],
                convenience_score=profile["convenience_score"],
                average_price_level=row["average_price_level"],
                default_portion_grams=row["default_portion_grams"],
                direct_eating=row["direct_eating"],
                consumption_mode=row["consumption_mode"],
                daily_recommendation_role=row["daily_recommendation_role"],
                preparation_difficulty=row["preparation_difficulty"],
                portability_score=row["portability_score"],
                messiness_score=row["messiness_score"],
                storage_difficulty=row["storage_difficulty"],
                aroma_intensity=row["aroma_intensity"],
                commonness_score=row["commonness_score"],
                novelty_level=row["novelty_level"],
                data_quality=row["data_quality"],
                is_active=row["is_active"],
                nutrition=NutritionProfile(
                    **{
                        key: float(values[key])
                        for key in (
                            "energy",
                            "vitamin_c",
                            "fiber",
                            "potassium",
                            "folate",
                            "carotenoids",
                        )
                    }
                ),
                seasons=tuple(seasons[row["name"]]),
                selection_options=tuple(options_by_code.get(row["code"], ())),
                texture_score=profile["texture_score"],
                ripe_storage_score=profile["ripe_storage_score"],
                typical_purchase_stage=profile["typical_purchase_stage"],
                ripening_note=profile["ripening_note"],
            )
        )
    return result


def make_user(**changes: object) -> RecommendationUser:
    values: dict[str, object] = {
        "region": "华东",
        "city": "苏州",
        "sweet_preference": None,
        "sour_preference": None,
        "soft_preference": None,
        "crisp_preference": None,
        "texture_preference": None,
        "price_level": 2,
        "convenience_preference": 0.5,
        "discovery_level": 1,
        "fruit_preferences": {},
    }
    values.update(changes)
    return RecommendationUser(**values)


def build_profiles() -> dict[str, RecommendationUser]:
    return {
        "low_budget": make_user(
            price_level=1, texture_preference=0.9, convenience_preference=0.9
        ),
        "sour_sweet": make_user(
            sweet_preference=0.8,
            sour_preference=0.8,
            texture_preference=0.7,
            convenience_preference=0.3,
        ),
        "sweet_soft": make_user(
            sweet_preference=0.9,
            sour_preference=0.3,
            texture_preference=0.1,
            price_level=3,
        ),
        "mango_forbidden": make_user(
            fruit_preferences={13: FruitPreference(is_forbidden=True)}
        ),
        "recently_ate_mango": make_user(),
        "untried_avocado_durian": make_user(
            fruit_preferences={
                22: FruitPreference(has_tried=False, willing_to_try=True),
                24: FruitPreference(has_tried=False, willing_to_try=True),
            }
        ),
        "cold_start": make_user(discovery_level=2),
    }


def context_for(profile_name: str) -> RecommendationContext:
    return RecommendationContext(
        month=7,
        today=date(2026, 7, 31),
        random_seed=20260731,
        history_events=(
            (HistoryEvent(13, date(2026, 7, 29)),)
            if profile_name == "recently_ate_mango"
            else ()
        ),
    )


def test_seven_fixed_profiles_are_executable_and_explainable() -> None:
    fruits = load_seed_fruits()
    profiles = build_profiles()
    assert tuple(profiles) == SEVEN_PROFILES

    for profile_name, user in profiles.items():
        context = context_for(profile_name)
        top_ten = score_candidates(fruits, user, context)[:10]
        result = recommend_fruits(fruits, user, context)

        assert len(top_ten) == 10
        assert all(
            top_ten[index].base_score >= top_ten[index + 1].base_score
            for index in range(len(top_ten) - 1)
        )
        assert len(result.items) == 2
        assert len({item.fruit.id for item in result.items}) == 2
        assert all(2 <= len(item.reasons) <= 4 for item in result.items)

        selected_ids = {item.fruit.id for item in result.items}
        if profile_name == "mango_forbidden":
            assert 13 not in selected_ids
        if profile_name == "untried_avocado_durian":
            assert not {22, 24} <= selected_ids
