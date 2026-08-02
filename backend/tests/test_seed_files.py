import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
FRUIT_FILE = DATA_ROOT / "fruits_seed.json"
NUTRITION_FILE = DATA_ROOT / "nutrition_demo.csv"
SEASON_FILE = DATA_ROOT / "seasons_demo.csv"
FACT_FILE = DATA_ROOT / "fruit_facts_seed.json"
REQUIRED_CODES = {
    "apple",
    "banana",
    "orange",
    "mandarin",
    "grape",
    "kiwifruit",
    "strawberry",
    "blueberry",
    "watermelon",
    "hami_melon",
    "peach",
    "pear",
    "mango",
    "pineapple",
    "dragon_fruit",
    "lychee",
    "longan",
    "cherry",
    "pomegranate",
    "pomelo",
    "papaya",
    "durian",
}
SCORE_FIELDS = {
    "sweet_score",
    "sour_score",
    "soft_score",
    "crisp_score",
    "convenience_score",
}
NUTRITION_FIELDS = {
    "energy",
    "vitamin_c",
    "fiber",
    "potassium",
    "folate",
    "carotenoids",
}


def load_fruits() -> list[dict[str, object]]:
    return json.loads(FRUIT_FILE.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_fruit_seed_has_required_unique_records_and_valid_ranges() -> None:
    fruits = load_fruits()
    names = [str(fruit["name"]) for fruit in fruits]
    codes = [str(fruit["code"]) for fruit in fruits]

    assert 20 <= len(fruits) <= 30
    assert len(names) == len(set(names))
    assert REQUIRED_CODES <= set(codes)
    assert len(codes) == len(set(codes))

    expected_fields = {
        "code",
        "name",
        "aliases",
        "category",
        "taste",
        *SCORE_FIELDS,
        "average_price_level",
        "default_portion",
        "default_portion_grams",
        "direct_eating",
        "consumption_mode",
        "daily_recommendation_role",
        "preparation_difficulty",
        "portability_score",
        "messiness_score",
        "storage_difficulty",
        "aroma_intensity",
        "commonness_score",
        "novelty_level",
        "data_quality",
        "data_source_note",
        "image_url",
        "description",
        "is_active",
    }
    for fruit in fruits:
        assert set(fruit) == expected_fields
        assert all(
            isinstance(fruit[field], str) and str(fruit[field]).strip()
            for field in (
                "code",
                "name",
                "category",
                "taste",
                "default_portion",
                "description",
            )
        )
        assert all(0 <= float(fruit[field]) <= 1 for field in SCORE_FIELDS)
        assert fruit["average_price_level"] in {1, 2, 3}
        assert fruit["consumption_mode"] in {"direct", "peel", "cut", "ingredient"}
        assert fruit["daily_recommendation_role"] in {"main", "exploration", "supporting"}
        assert fruit["data_quality"] in {"high", "medium", "low"}
        assert 0 <= int(fruit["novelty_level"]) <= 2
        assert float(fruit["default_portion_grams"]) > 0
        assert all(
            0 <= float(fruit[field]) <= 1
            for field in (
                "preparation_difficulty",
                "portability_score",
                "messiness_score",
                "storage_difficulty",
                "aroma_intensity",
                "commonness_score",
            )
        )
        assert fruit["image_url"] is None
        assert fruit["is_active"] is True


def test_nutrition_demo_uses_one_normalized_row_per_fruit() -> None:
    fruit_names = {str(fruit["name"]) for fruit in load_fruits()}
    rows = read_csv(NUTRITION_FILE)
    row_names = [row["fruit_name"] for row in rows]

    assert set(row_names) == fruit_names
    assert len(row_names) == len(set(row_names))
    assert set(rows[0]) == {"fruit_name", *NUTRITION_FIELDS}
    for row in rows:
        assert all(0 <= float(row[field]) <= 1 for field in NUTRITION_FIELDS)


def test_seasons_have_valid_unique_natural_keys_and_cross_year_rows() -> None:
    fruit_names = {str(fruit["name"]) for fruit in load_fruits()}
    rows = read_csv(SEASON_FILE)
    natural_keys = [
        (
            row["fruit_name"],
            row["region"],
            int(row["start_month"]),
            int(row["end_month"]),
        )
        for row in rows
    ]

    assert {row["fruit_name"] for row in rows} == fruit_names
    assert len(natural_keys) == len(set(natural_keys))
    assert any(start > end for _, _, start, end in natural_keys)
    for row in rows:
        assert row["region"].strip()
        assert 1 <= int(row["start_month"]) <= 12
        assert 1 <= int(row["end_month"]) <= 12
        assert 0 <= float(row["season_score"]) <= 1


def test_fruit_fact_seed_has_three_rows_per_fruit() -> None:
    facts = json.loads(FACT_FILE.read_text(encoding="utf-8"))
    fruit_codes = {str(fruit["code"]) for fruit in load_fruits()}
    keys = [(row["fruit_code"], row["sort_order"]) for row in facts]

    assert len(facts) == 72
    assert {row["fruit_code"] for row in facts} == fruit_codes
    assert len(keys) == len(set(keys))
    assert all(row["fact_type"] for row in facts)
    assert all(row["fact_text"].strip() for row in facts)
    assert all(row["sort_order"] in {1, 2, 3} for row in facts)
    assert all(row["is_active"] is True for row in facts)
    assert all(
        sum(1 for item in facts if item["fruit_code"] == code) == 3
        for code in fruit_codes
    )


def test_emitted_seed_sql_casts_empty_alias_arrays() -> None:
    from app.seed.seed_fruits import load_seed_dataset, render_seed_sql

    sql = render_seed_sql(load_seed_dataset())
    assert "ARRAY[]::VARCHAR(100)[]" in sql
    assert "ARRAY[]," not in sql


def test_readme_states_demo_scope_and_normalized_nutrition_contract() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.split())

    assert (
        "项目中的季节、价格和部分营养数据用于软件功能演示，"
        "不构成医学或专业营养建议。"
    ) in readme
    assert "归一化演示分数" in readme
    assert "不表示每 100 克的真实克数或毫克数" in normalized_readme
