from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from decimal import Decimal
import json
import os
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, String, column, func, select, text, values
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.database import create_database_engine
from app.models import Fruit, FruitNutrition, FruitSeason


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "data"
EXPECTED_ALEMBIC_VERSION = "0006"


class FruitSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=100)
    aliases: list[str] = Field(default_factory=list)
    category: str = Field(min_length=1, max_length=80)
    taste: str = Field(min_length=1, max_length=120)
    sweet_score: Decimal = Field(ge=0, le=1)
    sour_score: Decimal = Field(ge=0, le=1)
    soft_score: Decimal = Field(ge=0, le=1)
    crisp_score: Decimal = Field(ge=0, le=1)
    convenience_score: Decimal = Field(ge=0, le=1)
    average_price_level: int = Field(ge=1, le=3)
    default_portion: str = Field(min_length=1, max_length=80)
    default_portion_grams: Decimal = Field(gt=0)
    direct_eating: bool
    consumption_mode: str = Field(pattern="^(direct|peel|cut|ingredient)$")
    daily_recommendation_role: str = Field(
        pattern="^(main|exploration|supporting)$"
    )
    preparation_difficulty: Decimal = Field(ge=0, le=1)
    portability_score: Decimal = Field(ge=0, le=1)
    messiness_score: Decimal = Field(ge=0, le=1)
    storage_difficulty: Decimal = Field(ge=0, le=1)
    aroma_intensity: Decimal = Field(ge=0, le=1)
    commonness_score: Decimal = Field(ge=0, le=1)
    novelty_level: int = Field(ge=0, le=2)
    data_quality: str = Field(pattern="^(high|medium|low)$")
    data_source_note: str | None = Field(default=None, max_length=500)
    image_url: str | None = None
    description: str = Field(min_length=1)
    is_active: bool = True


class NutritionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fruit_name: str = Field(min_length=1, max_length=100)
    energy: Decimal = Field(ge=0, le=1)
    vitamin_c: Decimal = Field(ge=0, le=1)
    fiber: Decimal = Field(ge=0, le=1)
    potassium: Decimal = Field(ge=0, le=1)
    folate: Decimal = Field(ge=0, le=1)
    carotenoids: Decimal = Field(ge=0, le=1)


class SeasonSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fruit_name: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=100)
    region_level: str = Field(default="national", pattern="^(city|province|area|national)$")
    start_month: int = Field(ge=1, le=12)
    end_month: int = Field(ge=1, le=12)
    season_score: Decimal = Field(ge=0, le=1)
    availability_score: Decimal = Field(default=Decimal("0.45"), ge=0, le=1)
    supply_status: str = Field(
        default="unknown",
        pattern="^(available|unknown|unavailable)$",
    )


@dataclass(frozen=True)
class SeedDataset:
    fruits: tuple[FruitSeed, ...]
    nutritions: tuple[NutritionSeed, ...]
    seasons: tuple[SeasonSeed, ...]


@dataclass(frozen=True)
class SeedSummary:
    fruits: int
    nutritions: int
    seasons: int


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def require_unique(values: Sequence[object], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label} in seed files")


def load_seed_dataset(data_root: Path = DATA_ROOT) -> SeedDataset:
    fruit_payload = json.loads(
        (data_root / "fruits_seed.json").read_text(encoding="utf-8")
    )
    fruits = tuple(FruitSeed.model_validate(item) for item in fruit_payload)
    nutritions = tuple(
        NutritionSeed.model_validate(item)
        for item in read_csv(data_root / "nutrition_demo.csv")
    )
    season_rows = []
    for item in read_csv(data_root / "seasons_demo.csv"):
        row = dict(item)
        region = row.get("region", "")
        row.setdefault("region_level", "national" if region == "全国" else "area")
        row.setdefault(
            "availability_score",
            "0.9" if region != "全国" else "0.8",
        )
        row.setdefault("supply_status", "available")
        season_rows.append(SeasonSeed.model_validate(row))
    seasons = tuple(season_rows)

    fruit_names = [item.name for item in fruits]
    nutrition_names = [item.fruit_name for item in nutritions]
    season_keys = [
        (
            item.fruit_name,
            item.region,
            item.start_month,
            item.end_month,
        )
        for item in seasons
    ]
    require_unique(fruit_names, "fruit name")
    require_unique(nutrition_names, "nutrition fruit name")
    require_unique(season_keys, "season natural key")

    expected_names = set(fruit_names)
    if set(nutrition_names) != expected_names:
        raise ValueError("Nutrition rows must match fruit names exactly")
    if {item.fruit_name for item in seasons} != expected_names:
        raise ValueError("Every fruit must have season rows")

    return SeedDataset(
        fruits=fruits,
        nutritions=nutritions,
        seasons=seasons,
    )


def fruit_rows(dataset: SeedDataset) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in dataset.fruits:
        row = item.model_dump()
        if not row["aliases"]:
            row["aliases"] = postgresql.array([], type_=String(100))
        rows.append(row)
    return rows


def build_fruit_statement(dataset: SeedDataset) -> object:
    statement = insert(Fruit).values(fruit_rows(dataset))
    excluded = statement.excluded
    update_columns = {
        name: getattr(excluded, name)
        for name in (
            "category",
            "code",
            "aliases",
            "taste",
            "sweet_score",
            "sour_score",
            "soft_score",
            "crisp_score",
            "convenience_score",
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
        )
    }
    update_columns["updated_at"] = func.now()
    return statement.on_conflict_do_update(
        index_elements=[Fruit.name],
        set_=update_columns,
    )


def nutrition_values_table(dataset: SeedDataset) -> object:
    seed_values = values(
        column("fruit_name", String(100)),
        column("energy", FruitNutrition.energy.type),
        column("vitamin_c", FruitNutrition.vitamin_c.type),
        column("fiber", FruitNutrition.fiber.type),
        column("potassium", FruitNutrition.potassium.type),
        column("folate", FruitNutrition.folate.type),
        column("carotenoids", FruitNutrition.carotenoids.type),
        name="seed_nutrition",
    )
    return seed_values.data(
        [
            (
                item.fruit_name,
                item.energy,
                item.vitamin_c,
                item.fiber,
                item.potassium,
                item.folate,
                item.carotenoids,
            )
            for item in dataset.nutritions
        ]
    )


def build_nutrition_statement(dataset: SeedDataset) -> object:
    seed_values = nutrition_values_table(dataset)
    selected = select(
        Fruit.id,
        seed_values.c.energy,
        seed_values.c.vitamin_c,
        seed_values.c.fiber,
        seed_values.c.potassium,
        seed_values.c.folate,
        seed_values.c.carotenoids,
    ).join(seed_values, Fruit.name == seed_values.c.fruit_name)
    statement = insert(FruitNutrition).from_select(
        (
            "fruit_id",
            "energy",
            "vitamin_c",
            "fiber",
            "potassium",
            "folate",
            "carotenoids",
        ),
        selected,
    )
    excluded = statement.excluded
    return statement.on_conflict_do_update(
        index_elements=[FruitNutrition.fruit_id],
        set_={
            "energy": excluded.energy,
            "vitamin_c": excluded.vitamin_c,
            "fiber": excluded.fiber,
            "potassium": excluded.potassium,
            "folate": excluded.folate,
            "carotenoids": excluded.carotenoids,
            "updated_at": func.now(),
        },
    )


def season_values_table(dataset: SeedDataset) -> object:
    seed_values = values(
        column("fruit_name", String(100)),
        column("region", String(100)),
        column("region_level", String(20)),
        column("start_month", FruitSeason.start_month.type),
        column("end_month", FruitSeason.end_month.type),
        column("season_score", FruitSeason.season_score.type),
        column("availability_score", FruitSeason.season_score.type),
        column("supply_status", String(20)),
        name="seed_season",
    )
    return seed_values.data(
        [
            (
                item.fruit_name,
                item.region,
                item.region_level,
                item.start_month,
                item.end_month,
                item.season_score,
                item.availability_score,
                item.supply_status,
            )
            for item in dataset.seasons
        ]
    )


def build_season_statement(dataset: SeedDataset) -> object:
    seed_values = season_values_table(dataset)
    selected = select(
        Fruit.id,
        seed_values.c.region,
        seed_values.c.region_level,
        seed_values.c.start_month,
        seed_values.c.end_month,
        seed_values.c.season_score,
        seed_values.c.availability_score,
        seed_values.c.supply_status,
    ).join(seed_values, Fruit.name == seed_values.c.fruit_name)
    statement = insert(FruitSeason).from_select(
        (
            "fruit_id",
            "region",
            "region_level",
            "start_month",
            "end_month",
            "season_score",
            "availability_score",
            "supply_status",
        ),
        selected,
    )
    return statement.on_conflict_do_update(
        index_elements=[
            FruitSeason.fruit_id,
            FruitSeason.region,
            FruitSeason.start_month,
            FruitSeason.end_month,
        ],
        set_={
            "region_level": statement.excluded.region_level,
            "season_score": statement.excluded.season_score,
            "availability_score": statement.excluded.availability_score,
            "supply_status": statement.excluded.supply_status,
        },
    )


def seed_database(
    engine: Engine,
    dataset: SeedDataset,
    *,
    before_seasons: Callable[[], None] | None = None,
) -> SeedSummary:
    with engine.begin() as connection:
        version = connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one()
        if version != EXPECTED_ALEMBIC_VERSION:
            raise RuntimeError("Database schema is not at the expected version")

        connection.execute(build_fruit_statement(dataset))
        connection.execute(build_nutrition_statement(dataset))
        if before_seasons is not None:
            before_seasons()
        connection.execute(build_season_statement(dataset))

    return SeedSummary(
        fruits=len(dataset.fruits),
        nutritions=len(dataset.nutritions),
        seasons=len(dataset.seasons),
    )


def compile_statement(statement: object) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def render_seed_sql(dataset: SeedDataset) -> str:
    statements = (
        build_fruit_statement(dataset),
        build_nutrition_statement(dataset),
        build_season_statement(dataset),
    )
    return ";\n\n".join(compile_statement(item) for item in statements) + ";"


def create_checked_test_engine() -> Engine:
    if os.getenv("DAILY_FRUIT_ALLOW_TEST_DATABASE_WRITE") != "yes":
        raise RuntimeError(
            "DAILY_FRUIT_ALLOW_TEST_DATABASE_WRITE=yes is required"
        )
    settings = Settings()
    database_url = settings.test_database_url
    if database_url is None:
        raise RuntimeError("TEST_DATABASE_URL is not configured")
    parsed = urlsplit(database_url)
    if (
        parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.path.strip("/") != "daily_fruit_test"
    ):
        raise RuntimeError("Seed writes require the exact local test database")
    engine = create_database_engine("test", settings=settings)
    if engine is None:
        raise RuntimeError("TEST_DATABASE_URL is not configured")
    return engine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed daily-fruit demo data")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and summarize files without a database connection",
    )
    mode.add_argument(
        "--emit-sql",
        action="store_true",
        help="print PostgreSQL upsert SQL without a database connection",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)
    dataset = load_seed_dataset()
    summary = SeedSummary(
        fruits=len(dataset.fruits),
        nutritions=len(dataset.nutritions),
        seasons=len(dataset.seasons),
    )

    if options.dry_run:
        print(
            "Dry run validated: "
            f"fruits={summary.fruits}, "
            f"nutritions={summary.nutritions}, seasons={summary.seasons}"
        )
        return 0
    if options.emit_sql:
        print(render_seed_sql(dataset))
        return 0

    engine: Engine | None = None
    try:
        engine = create_checked_test_engine()
        summary = seed_database(engine, dataset)
    except (SQLAlchemyError, RuntimeError, ValueError):
        print("Seed failed; transaction rolled back.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()

    print(
        "Seed completed: "
        f"fruits={summary.fruits}, "
        f"nutritions={summary.nutritions}, seasons={summary.seasons}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
