import os
from pathlib import Path
import subprocess
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
def run_alembic(
    *arguments: str,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for variable_name in (
        "ALEMBIC_DATABASE_PURPOSE",
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "TEST_DATABASE_URL",
    ):
        environment.pop(variable_name, None)
    if extra_environment:
        environment.update(extra_environment)

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ALEMBIC_INI),
            *arguments,
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_alembic_history_works_without_database_configuration() -> None:
    result = run_alembic("history")

    assert result.returncode == 0
    assert "<base> -> 0001, create daily fruit tables" in result.stdout
    assert "0001 -> 0002" in result.stdout
    assert "0002 -> 0003" in result.stdout
    assert "0003 -> 0004" in result.stdout
    assert "0004 -> 0005" in result.stdout
    assert "0005 -> 0006 (head)" in result.stdout
    assert "postgresql" not in result.stdout
    assert "supabase" not in result.stdout.lower()


def test_alembic_ini_does_not_contain_a_database_url() -> None:
    contents = ALEMBIC_INI.read_text(encoding="utf-8")

    assert "sqlalchemy.url" not in contents
    assert "postgresql" not in contents
    assert "supabase" not in contents.lower()


def test_online_command_requires_explicit_database_purpose() -> None:
    secret = "must-not-appear"
    result = run_alembic(
        "current",
        extra_environment={
            "DATABASE_URL": (
                "postgresql+psycopg://fruit:"
                f"{secret}@localhost:5432/daily_fruit"
            )
        },
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "ALEMBIC_DATABASE_PURPOSE" in output
    assert secret not in output


def test_migration_purpose_never_falls_back_to_runtime_url() -> None:
    secret = "runtime-only-password"
    result = run_alembic(
        "current",
        extra_environment={
            "ALEMBIC_DATABASE_PURPOSE": "migration",
            "DATABASE_URL": (
                "postgresql+psycopg://fruit:"
                f"{secret}@localhost:5432/daily_fruit"
            ),
        },
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "MIGRATION_DATABASE_URL is not configured" in output
    assert secret not in output


def test_offline_sql_uses_test_metadata_without_connecting() -> None:
    secret = "offline-only-password"
    result = run_alembic(
        "upgrade",
        "head",
        "--sql",
        extra_environment={
            "ALEMBIC_DATABASE_PURPOSE": "test",
            "TEST_DATABASE_URL": (
                "postgresql+psycopg://fruit_test:"
                f"{secret}@127.0.0.1:9/daily_fruit_test"
            ),
        },
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0
    assert secret not in output
