from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0010_product_feedback.py"
)


def load_migration():
    spec = spec_from_file_location("daily_fruit_migration_0010", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_product_feedback_migration_has_single_linear_parent() -> None:
    migration = load_migration()

    assert migration.revision == "0010"
    assert migration.down_revision == "0009"


def test_product_feedback_migration_contains_backend_only_constraints() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    for expected in (
        "product_feedback",
        "ck_product_feedback_category_values",
        "ck_product_feedback_content_length",
        "ck_product_feedback_page_key_values",
        "ck_product_feedback_status_values",
        "ck_product_feedback_status_resolved_at_consistency",
        "ondelete=\"set null\"",
        "enable row level security",
        "revoke all privileges on table",
        "revoke all privileges on sequence",
    ):
        assert expected in source

    for forbidden in (
        "if not exists",
        "create policy",
        "auth.",
        "storage.",
        "truncate ",
    ):
        assert forbidden not in source


def test_product_feedback_migration_downgrade_is_table_scoped() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    assert 'op.drop_table("product_feedback"' in source
    assert "drop_table(\"users\"" not in source
    assert "drop_table(\"recommendations\"" not in source
