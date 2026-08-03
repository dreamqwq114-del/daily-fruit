import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.seed.seed_fruits import load_seed_dataset, seed_database


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def checked_test_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if os.getenv("DAILY_FRUIT_ALLOW_DESTRUCTIVE_TEST_DATABASE") != "yes":
        pytest.skip(
            "DAILY_FRUIT_ALLOW_DESTRUCTIVE_TEST_DATABASE=yes is required"
        )
    settings = Settings(_env_file=None, TEST_DATABASE_URL=database_url)
    assert settings.test_database_url == database_url
    parsed = urlsplit(database_url)
    assert parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.path.strip("/") == "daily_fruit_test"
    return database_url


def run_seed_cli(*arguments: str, database_url: str) -> str:
    environment = os.environ.copy()
    environment.update(
        TEST_DATABASE_URL=database_url,
        DAILY_FRUIT_ALLOW_TEST_DATABASE_WRITE="yes",
        PYTHONUTF8="1",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.seed.seed_fruits",
            *arguments,
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def counts(engine: Engine) -> tuple[int, int, int, int, int]:
    with engine.connect() as connection:
        return (
            connection.execute(text("SELECT count(*) FROM public.fruits"))
            .scalar_one(),
            connection.execute(
                text("SELECT count(*) FROM public.fruit_facts")
            ).scalar_one(),
            connection.execute(
                text("SELECT count(*) FROM public.fruit_nutritions")
            ).scalar_one(),
            connection.execute(
                text("SELECT count(*) FROM public.fruit_seasons")
            ).scalar_one(),
            connection.execute(
                text("SELECT count(*) FROM public.fruit_selection_options")
            ).scalar_one(),
        )


def test_seed_is_dry_run_transactional_and_idempotent() -> None:
    database_url = checked_test_url()
    engine = create_engine(database_url, poolclass=NullPool)
    dataset = load_seed_dataset()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM public.fruit_selection_options"))
        connection.execute(text("DELETE FROM public.fruit_facts"))
        connection.execute(text("DELETE FROM public.fruit_seasons"))
        connection.execute(text("DELETE FROM public.fruit_nutritions"))
        connection.execute(text("DELETE FROM public.fruits"))

    try:
        output = run_seed_cli("--dry-run", database_url=database_url)
        assert "Dry run validated" in output
        assert counts(engine) == (0, 0, 0, 0, 0)

        emitted_sql = run_seed_cli("--emit-sql", database_url=database_url)
        lowered_sql = emitted_sql.lower()
        assert lowered_sql.count("insert into public.") == 5
        assert "insert into public.fruits" in lowered_sql
        assert "insert into public.fruit_facts" in lowered_sql
        assert "insert into public.fruit_nutritions" in lowered_sql
        assert "insert into public.fruit_seasons" in lowered_sql
        assert "insert into public.fruit_selection_options" in lowered_sql
        assert "delete " not in lowered_sql
        assert "truncate " not in lowered_sql
        assert "public.users" not in lowered_sql
        assert "public.recommendations" not in lowered_sql
        assert counts(engine) == (0, 0, 0, 0, 0)

        run_seed_cli(database_url=database_url)
        first_counts = counts(engine)
        assert first_counts == (24, 72, 24, 48, 13)

        run_seed_cli(database_url=database_url)
        assert counts(engine) == first_counts

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE public.fruits
                    SET description = 'rollback sentinel'
                    WHERE name = '苹果'
                    """
                )
            )

        def fail_before_seasons() -> None:
            raise RuntimeError("intentional rollback test")

        with pytest.raises(RuntimeError, match="intentional rollback test"):
            seed_database(
                engine,
                dataset,
                before_seasons=fail_before_seasons,
            )

        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT description FROM public.fruits WHERE name='苹果'")
            ).scalar_one() == "rollback sentinel"
        assert counts(engine) == first_counts

        run_seed_cli(database_url=database_url)
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT description FROM public.fruits WHERE name='苹果'")
            ).scalar_one() != "rollback sentinel"
        assert counts(engine) == first_counts

        with engine.connect() as connection:
            assert connection.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) - count(DISTINCT name)
                       FROM public.fruits)
                    + (SELECT count(*) - count(DISTINCT (fruit_id, sort_order))
                       FROM public.fruit_facts)
                    + (SELECT count(*) - count(DISTINCT fruit_id)
                       FROM public.fruit_nutritions)
                    + (SELECT count(*) - count(DISTINCT
                         (fruit_id, region, start_month, end_month))
                       FROM public.fruit_seasons)
                    + (SELECT count(*) - count(DISTINCT (fruit_id, code))
                       FROM public.fruit_selection_options)
                    """
                )
            ).scalar_one() == 0
            assert connection.execute(
                text("SELECT count(*) FROM public.users")
            ).scalar_one() == 0
            assert connection.execute(
                text("SELECT count(*) FROM public.recommendations")
            ).scalar_one() == 0
            assert connection.execute(
                text("SELECT count(*) FROM public.recommendation_feedback")
            ).scalar_one() == 0
    finally:
        engine.dispose()
