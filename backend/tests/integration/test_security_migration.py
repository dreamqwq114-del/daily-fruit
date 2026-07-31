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


BACKEND_ROOT = Path(__file__).resolve().parents[2]
BUSINESS_TABLES = (
    "users",
    "fruits",
    "fruit_nutritions",
    "fruit_seasons",
    "user_fruit_preferences",
    "recommendations",
    "recommendation_items",
    "recommendation_feedback",
)
IDENTITY_SEQUENCES = tuple(f"{name}_id_seq" for name in BUSINESS_TABLES)


def run_alembic(*arguments: str, database_url: str) -> None:
    environment = os.environ.copy()
    environment.update(
        ALEMBIC_DATABASE_PURPOSE="test",
        TEST_DATABASE_URL=database_url,
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            *arguments,
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


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


def object_list(names: tuple[str, ...]) -> str:
    return ", ".join(f'public."{name}"' for name in names)


def prepare_insecure_test_baseline(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DO $test_roles$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_roles WHERE rolname = 'anon'
                    ) THEN
                        CREATE ROLE anon NOLOGIN;
                    END IF;
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_roles
                        WHERE rolname = 'authenticated'
                    ) THEN
                        CREATE ROLE authenticated NOLOGIN;
                    END IF;
                END
                $test_roles$;
                """
            )
        )
        assert connection.execute(
            text("SELECT to_regprocedure('public.rls_auto_enable()')")
        ).scalar_one_or_none() is None
        connection.execute(
            text(
                """
                CREATE FUNCTION public.rls_auto_enable()
                RETURNS event_trigger
                LANGUAGE plpgsql
                SECURITY DEFINER
                SET search_path = ''
                AS $test_function$
                BEGIN
                    NULL;
                END
                $test_function$
                """
            )
        )
        connection.execute(
            text(
                "GRANT ALL PRIVILEGES ON TABLE "
                f"{object_list(BUSINESS_TABLES)} TO anon, authenticated"
            )
        )
        connection.execute(
            text(
                "GRANT ALL PRIVILEGES ON SEQUENCE "
                f"{object_list(IDENTITY_SEQUENCES)} TO anon, authenticated"
            )
        )
        connection.execute(
            text(
                "GRANT EXECUTE ON FUNCTION public.rls_auto_enable() "
                "TO PUBLIC, anon, authenticated"
            )
        )


def assert_secure_state(engine: Engine) -> None:
    with engine.connect() as connection:
        rls_rows = connection.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity
                FROM pg_catalog.pg_class AS c
                JOIN pg_catalog.pg_namespace AS n
                  ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = ANY(:table_names)
                """
            ),
            {"table_names": list(BUSINESS_TABLES)},
        ).all()
        assert {name for name, _ in rls_rows} == set(BUSINESS_TABLES)
        assert all(enabled for _, enabled in rls_rows)

        policy_count = connection.execute(
            text(
                """
                SELECT count(*)
                FROM pg_catalog.pg_policy AS p
                JOIN pg_catalog.pg_class AS c ON c.oid = p.polrelid
                JOIN pg_catalog.pg_namespace AS n
                  ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = ANY(:table_names)
                """
            ),
            {"table_names": list(BUSINESS_TABLES)},
        ).scalar_one()
        assert policy_count == 0

        for role in ("anon", "authenticated"):
            for table_name in BUSINESS_TABLES:
                assert not connection.execute(
                    text(
                        """
                        SELECT has_table_privilege(
                            :role, :object_name,
                            'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'
                        )
                        """
                    ),
                    {
                        "role": role,
                        "object_name": f"public.{table_name}",
                    },
                ).scalar_one()
            for sequence_name in IDENTITY_SEQUENCES:
                assert not connection.execute(
                    text(
                        """
                        SELECT has_sequence_privilege(
                            :role, :object_name, 'USAGE,SELECT,UPDATE'
                        )
                        """
                    ),
                    {
                        "role": role,
                        "object_name": f"public.{sequence_name}",
                    },
                ).scalar_one()
            assert not connection.execute(
                text(
                    """
                    SELECT has_function_privilege(
                        :role, 'public.rls_auto_enable()', 'EXECUTE'
                    )
                    """
                ),
                {"role": role},
            ).scalar_one()


def test_security_migration_enforces_and_retains_deny_by_default() -> None:
    database_url = checked_test_url()
    engine = create_engine(database_url, poolclass=NullPool)
    try:
        run_alembic("downgrade", "0001", database_url=database_url)
        prepare_insecure_test_baseline(engine)
        run_alembic("upgrade", "0002", database_url=database_url)
        assert_secure_state(engine)

        run_alembic("downgrade", "0001", database_url=database_url)
        with engine.connect() as connection:
            assert not any(
                connection.execute(
                    text(
                        """
                        SELECT c.relrowsecurity
                        FROM pg_catalog.pg_class AS c
                        JOIN pg_catalog.pg_namespace AS n
                          ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public' AND c.relname = :name
                        """
                    ),
                    {"name": table_name},
                ).scalar_one()
                for table_name in BUSINESS_TABLES
            )
            assert not connection.execute(
                text(
                    """
                    SELECT has_function_privilege(
                        'anon', 'public.rls_auto_enable()', 'EXECUTE'
                    )
                    """
                )
            ).scalar_one()
        run_alembic("upgrade", "0002", database_url=database_url)
    finally:
        run_alembic("upgrade", "head", database_url=database_url)
        with engine.begin() as connection:
            if connection.execute(
                text("SELECT to_regprocedure('public.rls_auto_enable()')")
            ).scalar_one_or_none() is not None:
                connection.execute(
                    text("DROP FUNCTION public.rls_auto_enable()")
                )
        engine.dispose()
