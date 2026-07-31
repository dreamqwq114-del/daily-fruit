import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

from app.config import Settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]
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
EXPECTED_INDEXES = {
    "fruit_seasons": {"ix_fruit_seasons_region_fruit_id"},
    "recommendations": {
        "ix_recommendations_user_history",
        "uq_recommendations_active_user_date",
    },
    "user_fruit_preferences": {
        "ix_user_fruit_preferences_fruit_id"
    },
    "recommendation_items": {"ix_recommendation_items_fruit_id"},
    "recommendation_feedback": {
        "ix_recommendation_feedback_user_created_at"
    },
}


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


@pytest.fixture(scope="module")
def migrated_database() -> tuple[Engine, str]:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    destructive_confirmation = os.getenv(
        "DAILY_FRUIT_ALLOW_DESTRUCTIVE_TEST_DATABASE",
        "",
    )
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if destructive_confirmation != "yes":
        pytest.skip(
            "DAILY_FRUIT_ALLOW_DESTRUCTIVE_TEST_DATABASE=yes is required"
        )

    settings = Settings(_env_file=None, TEST_DATABASE_URL=database_url)
    assert settings.test_database_url == database_url
    parsed = urlsplit(database_url)
    assert parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.path.strip("/") == "daily_fruit_test"

    engine = create_engine(database_url, poolclass=NullPool)
    with engine.connect() as connection:
        existing = set(inspect(connection).get_table_names(schema="public"))
    unknown = existing - EXPECTED_TABLES - {"alembic_version"}
    assert not unknown, f"refusing to alter unknown test tables: {unknown}"

    run_alembic("downgrade", "base", database_url=database_url)
    run_alembic("upgrade", "0001", database_url=database_url)
    try:
        yield engine, database_url
    finally:
        engine.dispose()


def insert_user(connection: object) -> int:
    return connection.execute(
        text(
            """
            INSERT INTO public.users (
                username, city, region, sweet_preference,
                sour_preference, soft_preference, crisp_preference,
                price_level, convenience_preference
            ) VALUES (
                'migration-test', 'Suzhou', '华东', 0.7,
                0.3, 0.5, 0.8, 2, 0.9
            ) RETURNING id
            """
        )
    ).scalar_one()


def insert_fruit(connection: object, name: str) -> int:
    return connection.execute(
        text(
            """
            INSERT INTO public.fruits (
                name, category, taste, sweet_score, sour_score,
                soft_score, crisp_score, convenience_score,
                average_price_level, default_portion, description
            ) VALUES (
                :name, 'test', 'sweet', 0.8, 0.2,
                0.4, 0.7, 0.9, 2, '100 g', 'migration test'
            ) RETURNING id
            """
        ),
        {"name": name},
    ).scalar_one()


def test_upgrade_downgrade_upgrade_round_trip(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, database_url = migrated_database
    with engine.connect() as connection:
        assert set(inspect(connection).get_table_names(schema="public")) == (
            EXPECTED_TABLES | {"alembic_version"}
        )
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0001"

    run_alembic("downgrade", "base", database_url=database_url)
    with engine.connect() as connection:
        assert set(inspect(connection).get_table_names(schema="public")) == {
            "alembic_version"
        }

    run_alembic("upgrade", "0001", database_url=database_url)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0001"

    run_alembic("upgrade", "head", database_url=database_url)
    run_alembic("check", database_url=database_url)


def test_actual_indexes_and_foreign_key_delete_rules(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, _ = migrated_database
    with engine.connect() as connection:
        inspector = inspect(connection)
        for table_name, expected_names in EXPECTED_INDEXES.items():
            actual_names = {
                item["name"]
                for item in inspector.get_indexes(
                    table_name,
                    schema="public",
                )
            }
            assert expected_names <= actual_names

        actual_delete_rules: dict[tuple[str, str], str] = {}
        for table_name in EXPECTED_TABLES:
            for foreign_key in inspector.get_foreign_keys(
                table_name,
                schema="public",
            ):
                constrained_column = foreign_key["constrained_columns"][0]
                actual_delete_rules[(table_name, constrained_column)] = (
                    foreign_key["options"]["ondelete"]
                )

    assert actual_delete_rules == {
        ("fruit_nutritions", "fruit_id"): "CASCADE",
        ("fruit_seasons", "fruit_id"): "CASCADE",
        ("user_fruit_preferences", "user_id"): "CASCADE",
        ("user_fruit_preferences", "fruit_id"): "RESTRICT",
        ("recommendations", "user_id"): "RESTRICT",
        ("recommendation_items", "recommendation_id"): "CASCADE",
        ("recommendation_items", "fruit_id"): "RESTRICT",
        ("recommendation_feedback", "recommendation_item_id"): "CASCADE",
        ("recommendation_feedback", "user_id"): "RESTRICT",
    }


def test_database_constraints_and_cascades_are_enforced(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, _ = migrated_database
    connection = engine.connect()
    transaction = connection.begin()
    try:
        user_id = insert_user(connection)
        fruit_id = insert_fruit(connection, "migration-fruit-a")
        second_fruit_id = insert_fruit(connection, "migration-fruit-b")

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        INSERT INTO public.fruits (
                            name, category, taste, sweet_score, sour_score,
                            soft_score, crisp_score, convenience_score,
                            average_price_level, default_portion, description
                        ) VALUES (
                            'invalid-score', 'test', 'sweet', 1.1, 0.2,
                            0.4, 0.7, 0.9, 2, '100 g', 'invalid'
                        )
                        """
                    )
                )

        connection.execute(
            text(
                """
                INSERT INTO public.fruit_nutritions (
                    fruit_id, energy, vitamin_c, fiber,
                    potassium, folate, carotenoids
                ) VALUES (:fruit_id, 1, 1, 1, 1, 1, 1)
                """
            ),
            {"fruit_id": fruit_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO public.fruit_seasons (
                    fruit_id, region, start_month, end_month, season_score
                ) VALUES (:fruit_id, '华东', 12, 4, 0.9)
                """
            ),
            {"fruit_id": fruit_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO public.user_fruit_preferences (
                    user_id, fruit_id, preference_score, is_forbidden
                ) VALUES (:user_id, :fruit_id, 2, false)
                """
            ),
            {"user_id": user_id, "fruit_id": fruit_id},
        )
        recommendation_id = connection.execute(
            text(
                """
                INSERT INTO public.recommendations (
                    user_id, recommendation_date, refresh_number,
                    total_score, status
                ) VALUES (:user_id, '2026-07-31', 0, 0.8, 'active')
                RETURNING id
                """
            ),
            {"user_id": user_id},
        ).scalar_one()

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        INSERT INTO public.recommendations (
                            user_id, recommendation_date, refresh_number,
                            total_score, status
                        ) VALUES (
                            :user_id, '2026-07-31', 1, 0.7, 'active'
                        )
                        """
                    ),
                    {"user_id": user_id},
                )

        first_item_id = connection.execute(
            text(
                """
                INSERT INTO public.recommendation_items (
                    recommendation_id, fruit_id, score, rank, reasons
                ) VALUES (
                    :recommendation_id, :fruit_id, 0.8, 1,
                    '[{"code":"season","message":"in season"}]'
                ) RETURNING id
                """
            ),
            {
                "recommendation_id": recommendation_id,
                "fruit_id": fruit_id,
            },
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO public.recommendation_items (
                    recommendation_id, fruit_id, score, rank, reasons
                ) VALUES (
                    :recommendation_id, :fruit_id, 0.7, 2, '[]'
                )
                """
            ),
            {
                "recommendation_id": recommendation_id,
                "fruit_id": second_fruit_id,
            },
        )

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        INSERT INTO public.recommendation_items (
                            recommendation_id, fruit_id, score,
                            rank, reasons
                        ) VALUES (
                            :recommendation_id, :fruit_id, 0.6, 2, '[]'
                        )
                        """
                    ),
                    {
                        "recommendation_id": recommendation_id,
                        "fruit_id": fruit_id,
                    },
                )

        connection.execute(
            text(
                """
                INSERT INTO public.recommendation_feedback (
                    recommendation_item_id, user_id, feedback_type
                ) VALUES (:item_id, :user_id, 'liked')
                """
            ),
            {"item_id": first_item_id, "user_id": user_id},
        )

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text("DELETE FROM public.fruits WHERE id = :fruit_id"),
                    {"fruit_id": fruit_id},
                )

        connection.execute(
            text("DELETE FROM public.recommendations WHERE id = :id"),
            {"id": recommendation_id},
        )
        assert connection.execute(
            text(
                """
                SELECT count(*) FROM public.recommendation_items
                WHERE recommendation_id = :id
                """
            ),
            {"id": recommendation_id},
        ).scalar_one() == 0
        assert connection.execute(
            text(
                """
                SELECT count(*) FROM public.recommendation_feedback
                WHERE recommendation_item_id = :id
                """
            ),
            {"id": first_item_id},
        ).scalar_one() == 0

        connection.execute(
            text("DELETE FROM public.users WHERE id = :id"),
            {"id": user_id},
        )
        connection.execute(
            text("DELETE FROM public.fruits WHERE id = :id"),
            {"id": fruit_id},
        )
        assert connection.execute(
            text(
                """
                SELECT
                    (SELECT count(*) FROM public.fruit_nutritions
                     WHERE fruit_id = :id)
                  + (SELECT count(*) FROM public.fruit_seasons
                     WHERE fruit_id = :id)
                """
            ),
            {"id": fruit_id},
        ).scalar_one() == 0
    finally:
        transaction.rollback()
        connection.close()
