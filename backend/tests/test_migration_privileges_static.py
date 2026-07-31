from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0004_restrict_migration_table_privileges.py"
)


def test_migration_revokes_only_and_downgrade_never_regrants() -> None:
    spec = spec_from_file_location("daily_fruit_migration_0004", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    statements: list[str] = []
    migration.op = type(
        "Recorder",
        (),
        {"execute": staticmethod(lambda statement: statements.append(str(statement)))},
    )()

    migration.upgrade()
    sql = "\n".join(statements).lower()
    assert migration.revision == "0004"
    assert migration.down_revision == "0003"
    assert "revoke all privileges" in sql
    assert "public.alembic_version" in sql
    assert "from public" in sql
    assert "from anon" in sql
    assert "from authenticated" in sql
    assert " grant " not in f" {sql} "
    assert migration.downgrade() is None
