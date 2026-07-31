from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "0002_secure_daily_fruit_tables.py"
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


def load_migration() -> ModuleType:
    spec = spec_from_file_location("daily_fruit_migration_0002", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SqlRecorder:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: Any) -> None:
        self.statements.append(str(statement))


def run_function(name: str) -> tuple[ModuleType, list[str]]:
    migration = load_migration()
    recorder = SqlRecorder()
    migration.op = recorder
    getattr(migration, name)()
    return migration, recorder.statements


def table_names_in_rls_statements(statements: list[str]) -> set[str]:
    return {
        table_name
        for table_name in EXPECTED_TABLES
        if any(f'public."{table_name}"' in statement for statement in statements)
    }


def test_upgrade_enables_rls_on_exactly_the_eight_business_tables() -> None:
    migration, statements = run_function("upgrade")
    rls_statements = [
        statement
        for statement in statements
        if "ENABLE ROW LEVEL SECURITY" in statement
    ]

    assert migration.revision == "0002"
    assert migration.down_revision == "0001"
    assert len(rls_statements) == 8
    assert table_names_in_rls_statements(rls_statements) == EXPECTED_TABLES


def test_upgrade_revokes_tables_sequences_and_known_helper() -> None:
    migration, statements = run_function("upgrade")
    sql = "\n".join(statements)

    assert set(migration.DATA_API_ROLES) == {"anon", "authenticated"}
    assert "REVOKE ALL PRIVILEGES ON TABLE" in sql
    assert "REVOKE ALL PRIVILEGES ON SEQUENCE" in sql
    assert "FROM PUBLIC" in sql
    assert "FROM anon" in sql
    assert "FROM authenticated" in sql
    assert "to_regprocedure('public.rls_auto_enable()')" in sql
    assert "REVOKE EXECUTE ON FUNCTION public.rls_auto_enable()" in sql

    for table_name in EXPECTED_TABLES:
        assert f'public."{table_name}"' in sql
        assert f'public."{table_name}_id_seq"' in sql


def test_upgrade_creates_no_allow_policy_or_broad_grant() -> None:
    _, statements = run_function("upgrade")
    sql = "\n".join(statements).lower()

    assert "create policy" not in sql
    assert " grant " not in f" {sql} "
    assert "auth." not in sql
    assert "storage." not in sql
    assert "force row level security" not in sql


def test_downgrade_only_disables_rls_on_owned_tables() -> None:
    _, statements = run_function("downgrade")
    sql = "\n".join(statements).lower()

    assert len(statements) == 8
    assert all("disable row level security" in item.lower() for item in statements)
    assert table_names_in_rls_statements(statements) == EXPECTED_TABLES
    assert "grant " not in sql
    assert "drop " not in sql
    assert "auth." not in sql
    assert "storage." not in sql
