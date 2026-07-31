from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0003_link_users_to_supabase_auth.py"
)


class OperationRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def __getattr__(self, name: str):
        def record(*args: object, **kwargs: object) -> None:
            self.calls.append((name, args, kwargs))

        return record


def load_migration():
    spec = spec_from_file_location("daily_fruit_migration_0003", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_auth_migration_is_additive_and_scoped() -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    migration.op = recorder

    migration.upgrade()

    assert migration.revision == "0003"
    assert migration.down_revision == "0002"
    assert [call[0] for call in recorder.calls] == [
        "add_column",
        "create_unique_constraint",
        "create_foreign_key",
    ]
    foreign_key = recorder.calls[2]
    assert foreign_key[1][:3] == (
        "fk_users_auth_user_id_users",
        "users",
        "users",
    )
    assert foreign_key[2] == {
        "source_schema": "public",
        "referent_schema": "auth",
        "ondelete": "SET NULL",
    }


def test_auth_migration_downgrade_only_removes_its_objects() -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    migration.op = recorder

    migration.downgrade()

    assert [call[0] for call in recorder.calls] == [
        "drop_constraint",
        "drop_constraint",
        "drop_column",
    ]
    assert all(call[1][1] == "users" for call in recorder.calls[:2])
    assert recorder.calls[2][1][0] == "users"
    assert all(call[2]["schema"] == "public" for call in recorder.calls)
