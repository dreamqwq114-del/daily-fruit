from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

from sqlalchemy import CheckConstraint, Column, ForeignKeyConstraint, MetaData
from sqlalchemy import PrimaryKeyConstraint, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.models import Base


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "0001_create_daily_fruit_tables.py"
)
EXPECTED_TABLES = {
    "users",
    "fruits",
    "fruit_nutritions",
    "fruit_seasons",
    "user_fruit_preferences",
    "recommendations",
    "recommendation_items",
    "recommendation_feedback",
}
EXPECTED_INDEXES = {
    "ix_fruit_seasons_region_fruit_id",
    "ix_recommendations_user_history",
    "uq_recommendations_active_user_date",
    "ix_user_fruit_preferences_fruit_id",
    "ix_recommendation_items_fruit_id",
    "ix_recommendation_feedback_user_created_at",
}
V2_COLUMNS = {
    "fruits": {
        "code", "aliases", "default_portion_grams", "direct_eating",
        "consumption_mode", "daily_recommendation_role",
        "preparation_difficulty", "portability_score", "messiness_score",
        "storage_difficulty", "aroma_intensity", "commonness_score",
        "novelty_level", "data_quality", "data_source_note",
    },
    "fruit_seasons": {"region_level", "availability_score", "supply_status"},
    "users": {"discovery_level"},
    "user_fruit_preferences": {"has_tried", "willing_to_try"},
    "recommendation_items": {"individual_score", "pair_score", "nutrition_pair_score"},
}
V2_CONSTRAINTS = {
    "uq_fruits_code",
    "ck_fruits_default_portion_grams_positive",
    "ck_fruits_preparation_difficulty_range",
    "ck_fruits_portability_score_range",
    "ck_fruits_messiness_score_range",
    "ck_fruits_storage_difficulty_range",
    "ck_fruits_aroma_intensity_range",
    "ck_fruits_commonness_score_range",
    "ck_fruits_novelty_level_range",
    "ck_fruits_consumption_mode_values",
    "ck_fruits_daily_role_values",
    "ck_fruits_data_quality_values",
    "ck_fruit_seasons_region_level_values",
    "ck_fruit_seasons_availability_score_range",
    "ck_fruit_seasons_supply_status_values",
    "ck_users_discovery_level_range",
    "ck_recommendation_items_individual_score_range",
    "ck_recommendation_items_pair_score_range",
    "ck_recommendation_items_nutrition_pair_score_range",
    "ck_user_fruit_preferences_score_range",
    "ck_users_sweet_preference_range",
    "ck_users_sour_preference_range",
    "ck_users_soft_preference_range",
    "ck_users_crisp_preference_range",
}
V2_MODIFIED_COLUMNS = {
    ("user_fruit_preferences", "preference_score"),
    ("users", "sweet_preference"),
    ("users", "sour_preference"),
    ("users", "soft_preference"),
    ("users", "crisp_preference"),
}


def load_migration() -> ModuleType:
    spec = spec_from_file_location("daily_fruit_migration_0001", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OperationRecorder:
    def __init__(self) -> None:
        self.metadata = MetaData()
        self.created_tables: dict[str, Table] = {}
        self.created_indexes: dict[str, tuple[Any, ...]] = {}
        self.dropped_tables: list[str] = []
        self.dropped_indexes: list[str] = []

    @staticmethod
    def f(name: str) -> str:
        return name

    def create_table(
        self,
        name: str,
        *items: Any,
        **options: Any,
    ) -> None:
        assert options == {"schema": "public"}
        self.created_tables[name] = Table(
            name,
            self.metadata,
            *items,
            schema="public",
        )

    def create_index(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.created_indexes[name] = (args, kwargs)

    def drop_table(self, name: str, **kwargs: Any) -> None:
        assert kwargs == {"schema": "public"}
        self.dropped_tables.append(name)

    def drop_index(self, name: str, **kwargs: Any) -> None:
        assert kwargs["schema"] == "public"
        assert kwargs["table_name"] in EXPECTED_TABLES
        self.dropped_indexes.append(name)

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"unexpected Alembic operation: {name}")


def column_signature(column: Column[Any]) -> tuple[Any, ...]:
    dialect = postgresql.dialect()
    server_default = None
    if column.server_default is not None and column.identity is None:
        server_default = str(column.server_default.arg)
    identity_always = None
    if column.identity is not None:
        identity_always = column.identity.always
    return (
        column.name,
        str(column.type.compile(dialect=dialect)),
        column.nullable,
        server_default,
        identity_always,
    )


def constraint_signature(constraint: Any) -> tuple[Any, ...] | None:
    if isinstance(constraint, PrimaryKeyConstraint):
        return (
            "primary",
            constraint.name,
            tuple(column.name for column in constraint.columns),
        )
    if isinstance(constraint, UniqueConstraint):
        return (
            "unique",
            constraint.name,
            tuple(column.name for column in constraint.columns),
        )
    if isinstance(constraint, CheckConstraint):
        return ("check", constraint.name, str(constraint.sqltext))
    if isinstance(constraint, ForeignKeyConstraint):
        return (
            "foreign",
            constraint.name,
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
    return None


def test_upgrade_matches_the_eight_table_metadata_definitions() -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    migration.op = recorder

    migration.upgrade()

    assert migration.revision == "0001"
    assert migration.down_revision is None
    assert set(recorder.created_tables) == EXPECTED_TABLES
    assert set(recorder.created_indexes) == EXPECTED_INDEXES

    for table_name, actual in recorder.created_tables.items():
        expected = Base.metadata.tables[f"public.{table_name}"]
        actual_constraints = {
            signature
            for item in actual.constraints
            if item.name not in V2_CONSTRAINTS
            if (signature := constraint_signature(item)) is not None
        }
        expected_constraints = {
            signature
            for item in expected.constraints
            if item.name not in V2_CONSTRAINTS
            if not any(
                column.name == "auth_user_id"
                for column in getattr(item, "columns", ())
            )
            if (signature := constraint_signature(item)) is not None
        }

        assert [
            column_signature(item)
            for item in actual.columns
            if (table_name, item.name) not in V2_MODIFIED_COLUMNS
        ] == [
            column_signature(item)
            for item in expected.columns
            if item.name != "auth_user_id"
            and item.name not in V2_COLUMNS.get(table_name, set())
            and (table_name, item.name) not in V2_MODIFIED_COLUMNS
        ]
        assert actual_constraints == expected_constraints


def test_downgrade_only_removes_objects_owned_by_migration_0001() -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    migration.op = recorder

    migration.downgrade()

    assert recorder.dropped_tables == [
        "recommendation_feedback",
        "recommendation_items",
        "user_fruit_preferences",
        "recommendations",
        "fruit_seasons",
        "fruit_nutritions",
        "users",
        "fruits",
    ]
    assert set(recorder.dropped_indexes) == EXPECTED_INDEXES
    assert recorder.created_tables == {}
    assert recorder.created_indexes == {}


def test_migration_has_no_data_security_or_system_schema_operations() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    lowered = source.lower()

    for forbidden in (
        "if not exists",
        "auth.",
        "storage.",
        "op.execute",
        "op.bulk_insert",
        "op.alter_column",
        "op.drop_column",
        "op.drop_constraint",
        "op.drop_table('alembic_version'",
        "create policy",
        "enable row level security",
        "grant ",
        "revoke ",
        "truncate ",
    ):
        assert forbidden not in lowered
