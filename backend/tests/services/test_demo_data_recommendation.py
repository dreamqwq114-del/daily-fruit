import csv
import json
from collections import defaultdict
from pathlib import Path

from app.services import (
    NutritionProfile,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SeasonWindow,
    recommend_fruits,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def load_demo_fruits() -> list[RecommendationFruit]:
    fruits_data = json.loads(
        (PROJECT_ROOT / "data" / "fruits_seed.json").read_text(
            encoding="utf-8"
        )
    )
    with (PROJECT_ROOT / "data" / "nutrition_demo.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        nutrition_rows = {
            row["fruit_name"]: row for row in csv.DictReader(file)
        }
    seasons_by_name: dict[str, list[SeasonWindow]] = defaultdict(list)
    with (PROJECT_ROOT / "data" / "seasons_demo.csv").open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        for row in csv.DictReader(file):
            seasons_by_name[row["fruit_name"]].append(
                SeasonWindow(
                    region=row["region"],
                    start_month=int(row["start_month"]),
                    end_month=int(row["end_month"]),
                    season_score=float(row["season_score"]),
                )
            )

    fruits: list[RecommendationFruit] = []
    for fruit_id, row in enumerate(fruits_data, start=1):
        nutrition = nutrition_rows[row["name"]]
        fruits.append(
            RecommendationFruit(
                id=fruit_id,
                name=row["name"],
                sweet_score=row["sweet_score"],
                sour_score=row["sour_score"],
                soft_score=row["soft_score"],
                crisp_score=row["crisp_score"],
                convenience_score=row["convenience_score"],
                average_price_level=row["average_price_level"],
                is_active=row["is_active"],
                nutrition=NutritionProfile(
                    energy=float(nutrition["energy"]),
                    vitamin_c=float(nutrition["vitamin_c"]),
                    fiber=float(nutrition["fiber"]),
                    potassium=float(nutrition["potassium"]),
                    folate=float(nutrition["folate"]),
                    carotenoids=float(nutrition["carotenoids"]),
                ),
                seasons=tuple(seasons_by_name[row["name"]]),
            )
        )
    return fruits


def test_repository_demo_dataset_produces_explainable_pair_offline() -> None:
    fruits = load_demo_fruits()
    user = RecommendationUser(
        region="华东",
        sweet_preference=0.75,
        sour_preference=0.35,
        soft_preference=0.40,
        crisp_preference=0.80,
        price_level=2,
        convenience_preference=0.80,
    )

    result = recommend_fruits(
        fruits,
        user,
        RecommendationContext(month=7, random_seed=20260731),
    )

    assert len(fruits) == 24
    assert len(result.items) == 2
    assert len({item.fruit.id for item in result.items}) == 2
    assert all(2 <= len(item.reasons) <= 4 for item in result.items)
    assert all(0 <= item.score <= 1 for item in result.items)
