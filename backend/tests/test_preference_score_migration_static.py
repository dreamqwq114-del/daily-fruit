from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0011_allow_null_preference_score.py"
)


def load_migration():
    spec = spec_from_file_location("daily_fruit_migration_0011", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OperationRecorder:
    def __init__(self) -> None:
        self.alterations: list[tuple[str, str, bool, str]] = []

    def alter_column(
        self,
        table_name,
        column_name,
        *,
        existing_type,
        nullable,
        schema,
    ):
        self.alterations.append((table_name, column_name, nullable, schema))


def test_preference_score_migration_is_linear_and_scoped() -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    migration.op = recorder

    migration.upgrade()

    assert migration.revision == "0011"
    assert migration.down_revision == "0010"
    assert recorder.alterations == [
        ("user_fruit_preferences", "preference_score", True, "public")
    ]


def test_preference_score_migration_downgrade_restores_not_null() -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    migration.op = recorder

    migration.downgrade()

    assert recorder.alterations == [
        ("user_fruit_preferences", "preference_score", False, "public")
    ]


def test_preference_score_migration_does_not_write_rows_or_touch_system_schemas() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    for forbidden in (
        "op.execute",
        "insert ",
        "update ",
        "delete ",
        "truncate",
        "auth.",
        "storage.",
    ):
        assert forbidden not in source
