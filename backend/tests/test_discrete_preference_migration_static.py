from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "0014_enforce_discrete_fruit_preferences.py"
)


def migration_source() -> str:
    assert MIGRATION_PATH.exists(), "0014 discrete preference migration is required"
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_0014_is_linear_and_replaces_the_score_constraint() -> None:
    source = migration_source()
    assert 'revision: str = "0014"' in source
    assert 'down_revision: str | None = "0013"' in source
    assert 'drop_constraint("ck_user_fruit_preferences_score_range"' in source
    assert "preference_score IN (-1, 0, 1, 2)" in source


def test_0014_refuses_unknown_fractional_history_before_altering_schema() -> None:
    source = migration_source()
    read_position = source.index("preference_score NOT IN (-1, 0, 1, 2)")
    drop_position = source.index(
        'drop_constraint("ck_user_fruit_preferences_score_range"'
    )
    assert read_position < drop_position
    assert "raise RuntimeError" in source[read_position:drop_position]


def test_0014_refuses_invalid_willingness_history_without_rewriting_rows() -> None:
    source = migration_source()
    assert "willing_to_try IS NOT NULL" in source
    assert "has_tried IS DISTINCT FROM false" in source
    assert "ck_user_fruit_preferences_willingness_state" in source


def test_0014_downgrade_restores_only_the_legacy_range_constraint() -> None:
    source = migration_source()
    downgrade = source[source.index("def downgrade()") :]
    assert "preference_score BETWEEN -1 AND 2" in downgrade
    assert "UPDATE public.user_fruit_preferences" not in source
