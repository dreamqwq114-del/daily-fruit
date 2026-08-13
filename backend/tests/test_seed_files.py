import csv
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
FRUIT_FILE = DATA_ROOT / "fruits_seed.json"
NUTRITION_FILE = DATA_ROOT / "nutrition_demo.csv"
HARVEST_FILE = DATA_ROOT / "fruit_harvest_windows.csv"
MARKET_FILE = DATA_ROOT / "fruit_market_availability.csv"
FACT_FILE = DATA_ROOT / "fruit_facts_seed.json"
OPTION_FILE = DATA_ROOT / "fruit_selection_options_seed.json"
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
        "display_group",
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
        assert fruit["daily_recommendation_role"] in {"main", "supporting"}
        assert str(fruit["display_group"]).strip()
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


def test_harvest_and_market_rows_have_explicit_evidence_semantics() -> None:
    fruit_names = {str(fruit["name"]) for fruit in load_fruits()}
    harvest_rows = read_csv(HARVEST_FILE)
    market_rows = read_csv(MARKET_FILE)
    rows = harvest_rows + market_rows
    natural_keys = [
        (
            row["fruit_name"],
            "harvest" if row in harvest_rows else "market",
            row["region"],
            int(row["start_month"]),
            int(row["end_month"]),
        )
        for row in rows
    ]

    assert {row["fruit_name"] for row in harvest_rows} == fruit_names
    assert {row["fruit_name"] for row in market_rows} == fruit_names
    assert len(natural_keys) == len(set(natural_keys))
    for row in rows:
        assert row["region"].strip()
        assert (row["region"] == "全国") == (row["region_level"] == "national")
        assert 1 <= int(row["start_month"]) <= 12
        assert 1 <= int(row["end_month"]) <= 12
        assert row["data_quality"] in {"high", "medium", "low", "unverified"}
        assert row["is_scoring_enabled"] in {"true", "false"}
        if row["is_scoring_enabled"] == "true":
            assert row["data_quality"] != "unverified"
            assert "https://" in row["source_note"]
            assert 2000 <= int(row["source_year"]) <= 2100

    assert all(
        row["availability_level"] == "unknown"
        and row["data_quality"] == "unverified"
        and row["is_scoring_enabled"] == "false"
        for row in market_rows
    )


def test_corrected_harvest_examples_use_supported_production_regions() -> None:
    rows = read_csv(HARVEST_FILE)

    def matching(name: str) -> list[dict[str, str]]:
        return [row for row in rows if row["fruit_name"] == name]

    assert any(row["region"] == "西北" for row in matching("哈密瓜"))
    assert any(row["region"] == "西北" for row in matching("猕猴桃"))
    assert any(row["region"] == "西南" for row in matching("牛油果"))
    assert any(row["region"] == "西南" for row in matching("柠檬"))
    assert any(
        row["region"] == "西南" and int(row["end_month"]) >= 10
        for row in matching("芒果")
    )


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


def test_selection_option_seed_matches_the_calibrated_override_matrix() -> None:
    rows = json.loads(OPTION_FILE.read_text(encoding="utf-8"))
    score_fields = (
        "sweet_score",
        "sour_score",
        "texture_score",
        "convenience_score",
        "ripe_storage_score",
    )
    expected = {
        ("apple", "crisp"): {},
        ("apple", "powdery"): {
            "sweet_score": 0.70, "sour_score": 0.15, "texture_score": 0.25,
        },
        ("peach", "crisp"): {},
        ("peach", "soft"): {
            "sweet_score": 0.80, "sour_score": 0.20, "texture_score": 0.15,
            "convenience_score": 0.75, "ripe_storage_score": 0.10,
        },
        ("grape", "hard_crisp"): {},
        ("grape", "soft_juicy"): {
            "sweet_score": 0.70, "sour_score": 0.30, "texture_score": 0.20,
            "ripe_storage_score": 0.10,
        },
        ("kiwifruit", "green"): {},
        ("kiwifruit", "yellow"): {
            "sweet_score": 0.60, "sour_score": 0.40, "texture_score": 0.20,
        },
        ("kiwifruit", "red"): {
            "sweet_score": 0.65, "sour_score": 0.30, "texture_score": 0.20,
            "ripe_storage_score": 0.10,
        },
        ("pomegranate", "soft_seed"): {},
        ("pomegranate", "hard_seed"): {
            "sweet_score": 0.70, "sour_score": 0.25, "convenience_score": 0.20,
        },
        ("dragon_fruit", "red"): {},
        ("dragon_fruit", "white"): {
            "sweet_score": 0.50, "sour_score": 0.05, "texture_score": 0.40,
        },
    }

    actual = {
        (row["fruit_code"], row["code"]): {
            field: row[field] for field in score_fields if row.get(field) is not None
        }
        for row in rows
    }
    assert actual == expected
    assert all(
        all(row.get(field) is None for field in score_fields)
        for row in rows
        if row["is_default"]
    )


def test_emitted_seed_sql_casts_empty_alias_arrays() -> None:
    from app.seed.seed_fruits import load_seed_dataset, render_seed_sql

    sql = render_seed_sql(load_seed_dataset())
    assert "ARRAY[]::VARCHAR(100)[]" in sql
    assert "ARRAY[]," not in sql
    assert "update public.fruit_seasons" in sql.lower()
    assert "[daily-fruit-seed]" in sql


def test_migration_seed_rejects_a_different_supabase_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.seed import seed_fruits

    monkeypatch.setenv("DAILY_FRUIT_ALLOW_MIGRATION_SEED", "yes")
    monkeypatch.setenv(
        "MIGRATION_DATABASE_URL",
        "postgresql+psycopg://postgres:password@"
        "db.wrongproject.supabase.co:5432/postgres?sslmode=require",
    )
    monkeypatch.setenv(
        "SUPABASE_URL",
        "https://expectedproject.supabase.co",
    )

    with pytest.raises(RuntimeError, match="does not match"):
        seed_fruits.create_checked_migration_engine()


def test_migration_seed_accepts_matching_direct_project_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.seed import seed_fruits

    sentinel = object()
    monkeypatch.setenv("DAILY_FRUIT_ALLOW_MIGRATION_SEED", "yes")
    monkeypatch.setenv(
        "MIGRATION_DATABASE_URL",
        "postgresql+psycopg://postgres:password@"
        "db.expectedproject.supabase.co:5432/postgres?sslmode=require",
    )
    monkeypatch.setenv(
        "SUPABASE_URL",
        "https://expectedproject.supabase.co",
    )
    monkeypatch.setattr(
        seed_fruits,
        "create_database_engine",
        lambda purpose, *, settings: sentinel,
    )

    assert seed_fruits.create_checked_migration_engine() is sentinel


def test_readme_states_demo_scope_and_normalized_nutrition_contract() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.split())

    assert "采收月份仍是月级粗粒度资料" in readme
    assert "不代表实时库存、进口供应或用户附近商店一定可买到" in readme
    assert "市场可得性保持中性未知" in readme
    assert "归一化演示分数" in readme
    assert "不表示每 100 克的真实克数或毫克数" in normalized_readme
