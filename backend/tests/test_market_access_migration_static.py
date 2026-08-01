from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from sqlalchemy import Boolean, CheckConstraint, SmallInteger


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0007_user_market_access.py"
)


def load_migration():
    spec = spec_from_file_location("daily_fruit_migration_0007", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OperationRecorder:
    def __init__(self) -> None:
        self.added_columns: list[tuple[str, object, str]] = []
        self.created_checks: list[tuple[str, str, str, str]] = []
        self.dropped_columns: list[tuple[str, str]] = []
        self.dropped_checks: list[tuple[str, str, str, str]] = []

    def add_column(self, table_name, column, *, schema):
        self.added_columns.append((table_name, column, schema))

    def create_check_constraint(self, name, table_name, expression, *, schema):
        self.created_checks.append((name, table_name, expression, schema))

    def drop_column(self, table_name, column_name, *, schema):
        self.dropped_columns.append((table_name, column_name))

    def drop_constraint(self, name, table_name, *, schema, type_):
        self.dropped_checks.append((name, table_name, type_, schema))


def test_market_access_migration_is_additive_and_defaulted() -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    migration.op = recorder

    migration.upgrade()

    assert migration.revision == "0007"
    assert migration.down_revision == "0006"
    assert [item[0] for item in recorder.added_columns] == ["users", "users"]
    market_column = recorder.added_columns[0][1]
    online_column = recorder.added_columns[1][1]
    assert market_column.name == "market_access_level"
    assert isinstance(market_column.type, SmallInteger)
    assert market_column.nullable is False
    assert str(market_column.server_default.arg) == "2"
    assert online_column.name == "accepts_online_purchase"
    assert isinstance(online_column.type, Boolean)
    assert online_column.nullable is False
    assert str(online_column.server_default.arg) == "false"
    assert recorder.created_checks == [
        (
            "ck_users_market_access_level_range",
            "users",
            "market_access_level BETWEEN 1 AND 3",
            "public",
        )
    ]


def test_market_access_migration_downgrade_owns_only_new_objects() -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    migration.op = recorder

    migration.downgrade()

    assert recorder.dropped_columns == [
        ("users", "accepts_online_purchase"),
        ("users", "market_access_level"),
    ]
    assert recorder.dropped_checks == [
        (
            "ck_users_market_access_level_range",
            "users",
            "check",
            "public",
        )
    ]


def test_market_access_migration_does_not_touch_other_schemas_or_data() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8").lower()
    for forbidden in (
        "auth.",
        "storage.",
        "op.execute",
        "op.bulk_insert",
        "truncate",
        "delete ",
        "update ",
    ):
        assert forbidden not in source
