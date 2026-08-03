"""校验并幂等生成水果、营养和季节演示数据。

``--dry-run`` 和 ``--emit-sql`` 不连接数据库；默认写入只允许本地、可
丢弃的 ``daily_fruit_test``。生产 Supabase 写入必须同时显式传入
``--migration`` 和 ``DAILY_FRUIT_ALLOW_MIGRATION_SEED=yes``，避免把 seed
误当成无条件部署命令。
"""

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

from app.config import Settings, _is_supabase_host
from app.database import create_database_engine
from app.models import (
    Fruit,
    FruitFact,
    FruitNutrition,
    FruitSeason,
    FruitSelectionOption,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "data"
# 写入前的 schema 保护；该值必须与当前可写目标数据库的 alembic_version
# 同步，否则脚本应拒绝写入而不是猜测数据库状态。
EXPECTED_ALEMBIC_VERSION = "0012"

DISPLAY_GROUP_BY_CATEGORY = {
    "仁果": "苹果梨类",
    "核果类": "桃樱类",
    "浆果类": "葡萄与浆果类",
    "柑橘类": "柑橘类",
    "瓜果类": "瓜类",
    "热带水果": "热带与特色水果",
}

EXPLICIT_ONLY_OPTION_FRUITS = frozenset({"pomegranate"})


class FruitSeed(BaseModel):
    """fruits_seed.json 中一条水果身份和推荐演示属性。"""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=100)
    aliases: list[str] = Field(default_factory=list)
    category: str = Field(min_length=1, max_length=80)
    display_group: str | None = Field(default=None, min_length=1, max_length=80)
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
        pattern="^(main|supporting)$"
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
    """nutrition_demo.csv 中一条无物理单位的归一化演示分数。"""

    model_config = ConfigDict(extra="forbid")

    fruit_name: str = Field(min_length=1, max_length=100)
    energy: Decimal = Field(ge=0, le=1)
    vitamin_c: Decimal = Field(ge=0, le=1)
    fiber: Decimal = Field(ge=0, le=1)
    potassium: Decimal = Field(ge=0, le=1)
    folate: Decimal = Field(ge=0, le=1)
    carotenoids: Decimal = Field(ge=0, le=1)


class SeasonSeed(BaseModel):
    """seasons_demo.csv 中一条地区/月度季节窗口。"""

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


class FruitFactSeed(BaseModel):
    """fruit_facts_seed.json 涓殑涓€鏉℃按鏋滃喎鐭ヨ瘑銆?"""

    model_config = ConfigDict(extra="forbid")

    fruit_code: str = Field(min_length=1, max_length=60)
    fact_type: str = Field(pattern="^[a-z][a-z0-9_]{1,39}$")
    fact_text: str = Field(min_length=1, max_length=2000)
    sort_order: int = Field(ge=1, le=20)
    is_active: bool = True
    source_note: str | None = Field(default=None, max_length=500)


class SelectionOptionSeed(BaseModel):
    """父水果消费类型的演示性相对口感档案。"""

    model_config = ConfigDict(extra="forbid")

    fruit_code: str = Field(min_length=1, max_length=60)
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=100)
    sweet_score: Decimal | None = Field(default=None, ge=0, le=1)
    sour_score: Decimal | None = Field(default=None, ge=0, le=1)
    soft_score: Decimal | None = Field(default=None, ge=0, le=1)
    crisp_score: Decimal | None = Field(default=None, ge=0, le=1)
    is_default: bool = False
    is_active: bool = True
    display_order: int = Field(ge=1, le=100)
    data_quality: str = Field(default="low", pattern="^(high|medium|low)$")
    data_source_note: str | None = Field(default=None, max_length=500)


@dataclass(frozen=True)
class SeedDataset:
    fruits: tuple[FruitSeed, ...]
    nutritions: tuple[NutritionSeed, ...]
    seasons: tuple[SeasonSeed, ...]
    facts: tuple[FruitFactSeed, ...]
    selection_options: tuple[SelectionOptionSeed, ...]


@dataclass(frozen=True)
class SeedSummary:
    fruits: int
    nutritions: int
    seasons: int
    facts: int
    selection_options: int


def read_csv(path: Path) -> list[dict[str, str]]:
    """以 UTF-8 读取 CSV，统一去掉 BOM 并返回字典行。"""

    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def require_unique(values: Sequence[object], label: str) -> None:
    """拒绝重复主键/名称，防止 seed 生成不可预测 upsert。"""

    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label} in seed files")


def load_seed_dataset(data_root: Path = DATA_ROOT) -> SeedDataset:
    """加载并跨文件校验 24 水果、营养和季节引用关系。"""

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
    fact_payload = json.loads(
        (data_root / "fruit_facts_seed.json").read_text(encoding="utf-8")
    )
    facts = tuple(FruitFactSeed.model_validate(item) for item in fact_payload)
    option_payload = json.loads(
        (data_root / "fruit_selection_options_seed.json").read_text(encoding="utf-8")
    )
    selection_options = tuple(
        SelectionOptionSeed.model_validate(item) for item in option_payload
    )

    fruit_names = [item.name for item in fruits]
    fruit_codes = [item.code for item in fruits]
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
    fact_keys = [(item.fruit_code, item.sort_order) for item in facts]
    option_keys = [(item.fruit_code, item.code) for item in selection_options]
    require_unique(fruit_names, "fruit name")
    require_unique(fruit_codes, "fruit code")
    require_unique(nutrition_names, "nutrition fruit name")
    require_unique(season_keys, "season natural key")
    require_unique(fact_keys, "fruit fact natural key")
    require_unique(option_keys, "selection option natural key")

    expected_names = set(fruit_names)
    if set(nutrition_names) != expected_names:
        raise ValueError("Nutrition rows must match fruit names exactly")
    if {item.fruit_name for item in seasons} != expected_names:
        raise ValueError("Every fruit must have season rows")
    expected_codes = set(fruit_codes)
    if {item.fruit_code for item in facts} != expected_codes:
        raise ValueError("Every fruit must have fact rows")
    fact_counts = {
        code: sum(1 for item in facts if item.fruit_code == code)
        for code in expected_codes
    }
    if set(fact_counts.values()) != {3}:
        raise ValueError("Every fruit must have exactly three fact rows")

    option_fruit_codes = {item.fruit_code for item in selection_options}
    if not option_fruit_codes <= expected_codes:
        raise ValueError("Selection options must reference known fruit codes")
    for item in selection_options:
        if item.fruit_code in EXPLICIT_ONLY_OPTION_FRUITS and any(
            value is not None
            for value in (
                item.sweet_score,
                item.sour_score,
                item.soft_score,
                item.crisp_score,
            )
        ):
            raise ValueError(
                "Explicit-only selection options must not override fruit scores"
            )
    for fruit_code in option_fruit_codes:
        active = [
            item
            for item in selection_options
            if item.fruit_code == fruit_code and item.is_active
        ]
        if sum(item.is_default for item in active) != 1:
            raise ValueError(
                "Every fruit with selection options must have exactly one active default"
            )

    return SeedDataset(
        fruits=fruits,
        nutritions=nutritions,
        seasons=seasons,
        facts=facts,
        selection_options=selection_options,
    )


def fruit_rows(dataset: SeedDataset) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in dataset.fruits:
        row = item.model_dump()
        row["display_group"] = row["display_group"] or DISPLAY_GROUP_BY_CATEGORY[
            row["category"]
        ]
        # The four component fields are the single calculation source.  The
        # persisted aggregate remains only for compatibility with old clients.
        row["convenience_score"] = round(
            Decimal("0.30") * row["portability_score"]
            + Decimal("0.25") * (1 - row["preparation_difficulty"])
            + Decimal("0.25") * (1 - row["messiness_score"])
            + Decimal("0.20") * (1 - row["storage_difficulty"]),
            3,
        )
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
            "display_group",
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


def fact_values_table(dataset: SeedDataset) -> object:
    seed_values = values(
        column("fruit_code", String(60)),
        column("fact_type", String(40)),
        column("fact_text", FruitFact.fact_text.type),
        column("sort_order", FruitFact.sort_order.type),
        column("is_active", FruitFact.is_active.type),
        column("source_note", FruitFact.source_note.type),
        name="seed_fruit_fact",
    )
    return seed_values.data(
        [
            (
                item.fruit_code,
                item.fact_type,
                item.fact_text,
                item.sort_order,
                item.is_active,
                item.source_note,
            )
            for item in dataset.facts
        ]
    )


def build_fact_statement(dataset: SeedDataset) -> object:
    seed_values = fact_values_table(dataset)
    selected = select(
        Fruit.id,
        seed_values.c.fact_type,
        seed_values.c.fact_text,
        seed_values.c.sort_order,
        seed_values.c.is_active,
        seed_values.c.source_note,
    ).join(seed_values, Fruit.code == seed_values.c.fruit_code)
    statement = insert(FruitFact).from_select(
        (
            "fruit_id",
            "fact_type",
            "fact_text",
            "sort_order",
            "is_active",
            "source_note",
        ),
        selected,
    )
    return statement.on_conflict_do_update(
        index_elements=[FruitFact.fruit_id, FruitFact.sort_order],
        set_={
            "fact_type": statement.excluded.fact_type,
            "fact_text": statement.excluded.fact_text,
            "is_active": statement.excluded.is_active,
            "source_note": statement.excluded.source_note,
            "updated_at": func.now(),
        },
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


def selection_option_values_table(dataset: SeedDataset) -> object:
    """将 JSON 选项按父水果 code 批量映射，不在推荐循环内查询。"""

    seed_values = values(
        column("fruit_code", String(60)),
        column("code", String(40)),
        column("name", String(100)),
        column("sweet_score", FruitSelectionOption.sweet_score.type),
        column("sour_score", FruitSelectionOption.sour_score.type),
        column("soft_score", FruitSelectionOption.soft_score.type),
        column("crisp_score", FruitSelectionOption.crisp_score.type),
        column("is_default", FruitSelectionOption.is_default.type),
        column("is_active", FruitSelectionOption.is_active.type),
        column("display_order", FruitSelectionOption.display_order.type),
        column("data_quality", String(20)),
        column("data_source_note", FruitSelectionOption.data_source_note.type),
        name="seed_selection_option",
    )
    return seed_values.data(
        [
            (
                item.fruit_code,
                item.code,
                item.name,
                item.sweet_score,
                item.sour_score,
                item.soft_score,
                item.crisp_score,
                item.is_default,
                item.is_active,
                item.display_order,
                item.data_quality,
                item.data_source_note,
            )
            for item in dataset.selection_options
        ]
    )


def build_selection_option_statement(dataset: SeedDataset) -> object:
    seed_values = selection_option_values_table(dataset)
    selected = select(
        Fruit.id,
        seed_values.c.code,
        seed_values.c.name,
        seed_values.c.sweet_score,
        seed_values.c.sour_score,
        seed_values.c.soft_score,
        seed_values.c.crisp_score,
        seed_values.c.is_default,
        seed_values.c.is_active,
        seed_values.c.display_order,
        seed_values.c.data_quality,
        seed_values.c.data_source_note,
    ).join(seed_values, Fruit.code == seed_values.c.fruit_code)
    statement = insert(FruitSelectionOption).from_select(
        (
            "fruit_id",
            "code",
            "name",
            "sweet_score",
            "sour_score",
            "soft_score",
            "crisp_score",
            "is_default",
            "is_active",
            "display_order",
            "data_quality",
            "data_source_note",
        ),
        selected,
    )
    excluded = statement.excluded
    return statement.on_conflict_do_update(
        index_elements=[FruitSelectionOption.fruit_id, FruitSelectionOption.code],
        set_={
            "name": excluded.name,
            "sweet_score": excluded.sweet_score,
            "sour_score": excluded.sour_score,
            "soft_score": excluded.soft_score,
            "crisp_score": excluded.crisp_score,
            "is_default": excluded.is_default,
            "is_active": excluded.is_active,
            "display_order": excluded.display_order,
            "data_quality": excluded.data_quality,
            "data_source_note": excluded.data_source_note,
            "updated_at": func.now(),
        },
    )


def seed_database(
    engine: Engine,
    dataset: SeedDataset,
    *,
    before_seasons: Callable[[], None] | None = None,
) -> SeedSummary:
    """在单个事务中执行水果、营养、季节 upsert；失败由调用方回滚。"""

    with engine.begin() as connection:
        version = connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one()
        if version != EXPECTED_ALEMBIC_VERSION:
            raise RuntimeError("Database schema is not at the expected version")

        connection.execute(build_fruit_statement(dataset))
        connection.execute(build_selection_option_statement(dataset))
        connection.execute(build_fact_statement(dataset))
        connection.execute(build_nutrition_statement(dataset))
        if before_seasons is not None:
            before_seasons()
        connection.execute(build_season_statement(dataset))

    return SeedSummary(
        fruits=len(dataset.fruits),
        nutritions=len(dataset.nutritions),
        seasons=len(dataset.seasons),
        facts=len(dataset.facts),
        selection_options=len(dataset.selection_options),
    )


def compile_statement(statement: object) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def render_seed_sql(dataset: SeedDataset) -> str:
    """生成可审阅的 PostgreSQL upsert SQL，不建立连接。"""

    statements = (
        build_fruit_statement(dataset),
        build_selection_option_statement(dataset),
        build_fact_statement(dataset),
        build_nutrition_statement(dataset),
        build_season_statement(dataset),
    )
    return ";\n\n".join(compile_statement(item) for item in statements) + ";"


def create_checked_test_engine() -> Engine:
    """只创建精确匹配 localhost/daily_fruit_test 的测试 engine。"""

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


def create_checked_migration_engine() -> Engine:
    """创建仅用于明确授权的 Supabase migration seed engine。"""

    if os.getenv("DAILY_FRUIT_ALLOW_MIGRATION_SEED") != "yes":
        raise RuntimeError(
            "DAILY_FRUIT_ALLOW_MIGRATION_SEED=yes is required"
        )
    settings = Settings()
    database_url = settings.migration_database_url
    if database_url is None:
        raise RuntimeError("MIGRATION_DATABASE_URL is not configured")
    parsed = urlsplit(database_url)
    if not _is_supabase_host(parsed.hostname or ""):
        raise RuntimeError(
            "Migration seed requires a confirmed Supabase migration database"
        )
    engine = create_database_engine("migration", settings=settings)
    if engine is None:
        raise RuntimeError("MIGRATION_DATABASE_URL is not configured")
    return engine


def build_parser() -> argparse.ArgumentParser:
    """定义 dry-run、emit-sql 和受保护本地写入模式。"""

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
    mode.add_argument(
        "--migration",
        action="store_true",
        help="write the confirmed Supabase migration database with explicit approval",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """执行数据校验和选定 seed 模式，并返回 shell exit code。"""

    options = build_parser().parse_args(arguments)
    dataset = load_seed_dataset()
    summary = SeedSummary(
        fruits=len(dataset.fruits),
        nutritions=len(dataset.nutritions),
        seasons=len(dataset.seasons),
        facts=len(dataset.facts),
        selection_options=len(dataset.selection_options),
    )

    if options.dry_run:
        print(
            "Dry run validated: "
            f"fruits={summary.fruits}, "
            f"facts={summary.facts}, "
            f"nutritions={summary.nutritions}, seasons={summary.seasons}"
            f", selection_options={summary.selection_options}"
        )
        return 0
    if options.emit_sql:
        print(render_seed_sql(dataset))
        return 0

    engine: Engine | None = None
    try:
        engine = (
            create_checked_migration_engine()
            if options.migration
            else create_checked_test_engine()
        )
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
        f"facts={summary.facts}, "
        f"nutritions={summary.nutritions}, seasons={summary.seasons}"
        f", selection_options={summary.selection_options}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
