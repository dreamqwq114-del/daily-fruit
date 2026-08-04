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
    "fruit_facts",
    "fruit_nutritions",
    "fruit_seasons",
    "user_fruit_preferences",
    "recommendations",
    "recommendation_items",
    "recommendation_feedback",
    "product_feedback",
    "fruit_selection_options",
    "user_fruit_option_preferences",
}
INITIAL_TABLES = {
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
    "fruit_facts": {"ix_fruit_facts_fruit_active"},
    "fruit_seasons": {"ix_fruit_seasons_region_fruit_id"},
    "recommendations": {
        "ix_recommendations_user_history",
        "uq_recommendations_active_user_date",
    },
    "user_fruit_preferences": {
        "ix_user_fruit_preferences_fruit_id"
    },
    "recommendation_items": {
        "ix_recommendation_items_fruit_id",
        "ix_recommendation_items_selection_option_id",
    },
    "recommendation_feedback": {
        "ix_recommendation_feedback_user_created_at"
    },
    "product_feedback": {
        "ix_product_feedback_status_created_at",
        "ix_product_feedback_user_id",
    },
    "fruit_selection_options": {
        "ix_fruit_selection_options_fruit_active_order",
        "uq_fruit_selection_options_active_default",
    },
    "user_fruit_option_preferences": {
        "ix_user_fruit_option_preferences_user_fruit",
        "ix_user_fruit_option_preferences_fruit_id",
        "ix_user_fruit_option_preferences_option_id",
    },
}


def invoke_alembic(
    *arguments: str,
    database_url: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        ALEMBIC_DATABASE_PURPOSE="test",
        TEST_DATABASE_URL=database_url,
    )
    return subprocess.run(
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


def run_alembic(*arguments: str, database_url: str) -> None:
    result = invoke_alembic(*arguments, database_url=database_url)
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
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "auth" not in inspector.get_schema_names():
            connection.execute(text("CREATE SCHEMA auth"))
        auth_tables = set(inspect(connection).get_table_names(schema="auth"))
        assert auth_tables <= {"users"}, (
            f"refusing to alter unknown auth test tables: {auth_tables}"
        )
        if "users" not in auth_tables:
            connection.execute(
                text(
                    "CREATE TABLE auth.users ("
                    "id UUID PRIMARY KEY"
                    ")"
                )
            )
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
                code, name, aliases, category, display_group, taste,
                sweet_score, sour_score,
                soft_score, crisp_score, convenience_score,
                average_price_level, default_portion, default_portion_grams,
                direct_eating, consumption_mode, daily_recommendation_role,
                preparation_difficulty, portability_score, messiness_score,
                storage_difficulty, aroma_intensity, commonness_score,
                novelty_level, data_quality, description,
                texture_score, ripe_storage_score, typical_purchase_stage
            ) VALUES (
                :code, :name, ARRAY[]::VARCHAR(100)[], 'test', 'test', 'sweet',
                0.8, 0.2, 0.4, 0.7, 0.9, 2, '100 g', 100,
                true, 'direct', 'main', 0.5, 0.5, 0.5,
                0.5, 0.5, 0.5, 1, 'low', 'migration test',
                0.7, 0.5, 'ready_to_eat'
            ) RETURNING id
            """
        ),
        {"code": name, "name": name},
    ).scalar_one()


def insert_0012_fruit(connection: object, code: str, name: str) -> int:
    return connection.execute(
        text(
            """
            INSERT INTO public.fruits (
                code, name, aliases, category, display_group, taste,
                sweet_score, sour_score, soft_score, crisp_score,
                convenience_score, average_price_level, default_portion,
                default_portion_grams, direct_eating, consumption_mode,
                daily_recommendation_role, preparation_difficulty,
                portability_score, messiness_score, storage_difficulty,
                aroma_intensity, commonness_score, novelty_level,
                data_quality, description
            ) VALUES (
                :code, :name, ARRAY[]::VARCHAR(100)[], 'test', 'test', 'sweet',
                0.8, 0.2, 0.4, 0.7, 0.9, 2, '100 g', 100,
                true, 'direct', 'main', 0.5, 0.5, 0.5, 0.5,
                0.5, 0.5, 1, 'low', '0012 migration fixture'
            ) RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()


def test_upgrade_downgrade_upgrade_round_trip(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, database_url = migrated_database
    with engine.connect() as connection:
        assert set(inspect(connection).get_table_names(schema="public")) == (
            INITIAL_TABLES | {"alembic_version"}
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

    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0013"
        users_columns = {
            item["name"]
            for item in inspect(connection).get_columns(
                "users",
                schema="public",
            )
        }
        assert "auth_user_id" in users_columns


def test_0013_preserves_legacy_scores_freezes_history_and_migrates_users(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, database_url = migrated_database
    run_alembic("downgrade", "0012", database_url=database_url)
    with engine.begin() as connection:
        fruit_id = insert_0012_fruit(connection, "apple", "迁移苹果")
        option_id = connection.execute(
            text(
                """
                INSERT INTO public.fruit_selection_options (
                    fruit_id, code, name, sweet_score, sour_score,
                    soft_score, crisp_score, is_default, display_order
                ) VALUES (
                    :fruit_id, 'crisp', '旧清脆型', 0.61, 0.19,
                    0.23, 0.91, true, 1
                ) RETURNING id
                """
            ),
            {"fruit_id": fruit_id},
        ).scalar_one()
        users: dict[str, int] = {}
        for username, soft, crisp in (
            ("consistent", 0.2, 0.8),
            ("conflict", 0.1, 0.1),
            ("soft-only", 0.3, None),
            ("crisp-only", None, 0.7),
        ):
            users[username] = connection.execute(
                text(
                    """
                    INSERT INTO public.users (
                        username, city, region, sweet_preference,
                        sour_preference, soft_preference, crisp_preference,
                        price_level, convenience_preference
                    ) VALUES (
                        :username, 'Suzhou', '华东', 0.7, 0.3,
                        :soft, :crisp, 2, 0.9
                    ) RETURNING id
                    """
                ),
                {"username": username, "soft": soft, "crisp": crisp},
            ).scalar_one()
        recommendation_id = connection.execute(
            text(
                """
                INSERT INTO public.recommendations (
                    user_id, recommendation_date, refresh_number,
                    total_score, status
                ) VALUES (:user_id, '2026-08-01', 0, 0.8, 'active')
                RETURNING id
                """
            ),
            {"user_id": users["consistent"]},
        ).scalar_one()
        item_id = connection.execute(
            text(
                """
                INSERT INTO public.recommendation_items (
                    recommendation_id, fruit_id, score, individual_score,
                    pair_score, nutrition_pair_score, rank, reasons,
                    selection_option_id
                ) VALUES (
                    :recommendation_id, :fruit_id, 0.8, 0.8,
                    0.8, 0.5, 1, '[]', :option_id
                ) RETURNING id
                """
            ),
            {
                "recommendation_id": recommendation_id,
                "fruit_id": fruit_id,
                "option_id": option_id,
            },
        ).scalar_one()

    run_alembic("upgrade", "head", database_url=database_url)
    with engine.connect() as connection:
        option = connection.execute(
            text(
                """
                SELECT sweet_score, sour_score, soft_score, crisp_score,
                       texture_score, ripe_storage_score, convenience_score,
                       legacy_score_snapshot
                FROM public.fruit_selection_options WHERE id = :id
                """
            ),
            {"id": option_id},
        ).mappings().one()
        assert all(
            option[field] is None
            for field in (
                "sweet_score", "sour_score", "soft_score", "crisp_score",
                "texture_score", "ripe_storage_score", "convenience_score",
            )
        )
        assert option["legacy_score_snapshot"] == {
            "sweet_score": 0.61,
            "sour_score": 0.19,
            "soft_score": 0.23,
            "crisp_score": 0.91,
        }
        sources = {
            row.username: row.texture_preference_source
            for row in connection.execute(text(
                "SELECT username, texture_preference_source FROM public.users"
            ))
        }
        assert sources == {
            "consistent": "migrated_consistent",
            "conflict": "legacy_conflict",
            "soft-only": "migrated_from_soft",
            "crisp-only": "migrated_from_crisp",
        }
        snapshot = connection.execute(
            text(
                "SELECT fruit_snapshot FROM public.recommendation_items "
                "WHERE id = :id"
            ),
            {"id": item_id},
        ).scalar_one()
        assert snapshot["code"] == "apple"
        assert connection.execute(
            text(
                "SELECT scoring_model_version FROM public.recommendations "
                "WHERE id = :id"
            ),
            {"id": recommendation_id},
        ).scalar_one() == "taste-v1"
        option_snapshots = connection.execute(
            text(
                "SELECT selection_option_code_snapshot, "
                "selection_option_name_snapshot "
                "FROM public.recommendation_items WHERE id = :id"
            ),
            {"id": item_id},
        ).one()
        assert tuple(option_snapshots) == ("crisp", "旧清脆型")

    run_alembic("downgrade", "0012", database_url=database_url)
    with engine.connect() as connection:
        restored = connection.execute(
            text(
                "SELECT sweet_score, sour_score, soft_score, crisp_score "
                "FROM public.fruit_selection_options WHERE id = :id"
            ),
            {"id": option_id},
        ).one()
        assert tuple(float(value) for value in restored) == (0.61, 0.19, 0.23, 0.91)
        restored_soft = connection.execute(
            text("SELECT soft_preference FROM public.users WHERE username='consistent'")
        ).scalar_one()
        assert float(restored_soft) == pytest.approx(0.2)

    run_alembic("upgrade", "head", database_url=database_url)
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM public.recommendations WHERE id = :id"),
            {"id": recommendation_id},
        )
        connection.execute(text("DELETE FROM public.users"))
        connection.execute(
            text("DELETE FROM public.fruit_selection_options WHERE fruit_id = :id"),
            {"id": fruit_id},
        )
        connection.execute(
            text("DELETE FROM public.fruits WHERE id = :id"),
            {"id": fruit_id},
        )


def test_0013_unknown_fruit_fails_transactionally(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, database_url = migrated_database
    run_alembic("downgrade", "0012", database_url=database_url)
    with engine.begin() as connection:
        fruit_id = insert_0012_fruit(connection, "unknown-fixture", "未知迁移水果")

    result = invoke_alembic("upgrade", "head", database_url=database_url)
    assert result.returncode != 0
    assert "fruit profile backfill incomplete" in result.stdout + result.stderr
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0012"
        assert "texture_score" not in {
            column["name"]
            for column in inspect(connection).get_columns("fruits", schema="public")
        }
        assert "texture_preference" not in {
            column["name"]
            for column in inspect(connection).get_columns("users", schema="public")
        }
        assert "legacy_score_snapshot" not in {
            column["name"]
            for column in inspect(connection).get_columns(
                "fruit_selection_options", schema="public"
            )
        }
        assert "scoring_model_version" not in {
            column["name"]
            for column in inspect(connection).get_columns(
                "recommendations", schema="public"
            )
        }
        preference_score = next(
            column
            for column in inspect(connection).get_columns(
                "user_fruit_preferences", schema="public"
            )
            if column["name"] == "preference_score"
        )
        assert "0" in str(preference_score["default"])
        assert connection.execute(
            text("SELECT count(*) FROM public.fruits WHERE id = :id"),
            {"id": fruit_id},
        ).scalar_one() == 1
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM public.fruits WHERE id = :id"), {"id": fruit_id}
        )
    run_alembic("upgrade", "head", database_url=database_url)


def test_actual_indexes_and_foreign_key_delete_rules(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, database_url = migrated_database
    run_alembic("upgrade", "head", database_url=database_url)
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
        ("fruit_facts", "fruit_id"): "CASCADE",
        ("user_fruit_preferences", "user_id"): "CASCADE",
        ("user_fruit_preferences", "fruit_id"): "RESTRICT",
        ("recommendations", "user_id"): "RESTRICT",
        ("recommendation_items", "recommendation_id"): "CASCADE",
        ("recommendation_items", "fruit_id"): "RESTRICT",
        ("recommendation_feedback", "recommendation_item_id"): "CASCADE",
        ("recommendation_feedback", "user_id"): "RESTRICT",
        ("users", "auth_user_id"): "SET NULL",
        ("product_feedback", "user_id"): "SET NULL",
        ("fruit_selection_options", "fruit_id"): "RESTRICT",
        ("recommendation_items", "selection_option_id"): "RESTRICT",
        ("user_fruit_option_preferences", "fruit_id"): "RESTRICT",
        ("user_fruit_option_preferences", "user_id"): "CASCADE",
    }


def test_product_feedback_constraints_and_user_deidentification(
    migrated_database: tuple[Engine, str],
) -> None:
    """The new table rejects invalid values and nulls ownership on deletion."""

    engine, database_url = migrated_database
    run_alembic("upgrade", "head", database_url=database_url)
    connection = engine.connect()
    transaction = connection.begin()
    try:
        user_id = insert_user(connection)
        feedback_id = connection.execute(
            text(
                """
                INSERT INTO public.product_feedback (
                    user_id, category, content, page_key
                ) VALUES (:user_id, 'bug', 'A valid report', 'today')
                RETURNING id
                """
            ),
            {"user_id": user_id},
        ).scalar_one()

        invalid_rows = (
            {
                "category": "not-a-category",
                "content": "A valid report",
                "page_key": "today",
                "status": "new",
                "resolved_at": None,
            },
            {
                "category": "bug",
                "content": "   ",
                "page_key": "today",
                "status": "new",
                "resolved_at": None,
            },
            {
                "category": "bug",
                "content": "A valid report",
                "page_key": "settings",
                "status": "new",
                "resolved_at": None,
            },
            {
                "category": "bug",
                "content": "A valid report",
                "page_key": "today",
                "status": "new",
                "resolved_at": "2026-08-03 00:00:00+00",
            },
            {
                "category": "bug",
                "content": "A valid report",
                "page_key": "today",
                "status": "resolved",
                "resolved_at": None,
            },
        )
        for row in invalid_rows:
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(
                        text(
                            """
                            INSERT INTO public.product_feedback (
                                user_id, category, content, page_key,
                                status, resolved_at
                            ) VALUES (
                                :user_id, :category, :content, :page_key,
                                :status, :resolved_at
                            )
                            """
                        ),
                        {"user_id": user_id, **row},
                    )

        connection.execute(
            text("DELETE FROM public.users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        assert connection.execute(
            text(
                """
                SELECT user_id FROM public.product_feedback WHERE id = :id
                """
            ),
            {"id": feedback_id},
        ).scalar_one() is None
    finally:
        transaction.rollback()
        connection.close()


def test_database_constraints_and_cascades_are_enforced(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, database_url = migrated_database
    run_alembic("upgrade", "head", database_url=database_url)
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
                    total_score, status, scoring_model_version,
                    fruit_profile_version
                ) VALUES (
                    :user_id, '2026-07-31', 0, 0.8, 'active',
                    'taste-v1', 'migration-test-profile'
                )
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
                            total_score, status, scoring_model_version,
                            fruit_profile_version
                        ) VALUES (
                            :user_id, '2026-07-31', 1, 0.7, 'active',
                            'taste-v1', 'migration-test-profile'
                        )
                        """
                    ),
                    {"user_id": user_id},
                )

        first_item_id = connection.execute(
            text(
                """
                INSERT INTO public.recommendation_items (
                    recommendation_id, fruit_id, score, individual_score,
                    pair_score, nutrition_pair_score, rank, reasons,
                    fruit_snapshot
                ) VALUES (
                    :recommendation_id, :fruit_id, 0.8, 0.8,
                    0.75, 0.6, 1,
                    '[{"code":"season","message":"in season"}]', '{}'
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
                    recommendation_id, fruit_id, score, individual_score,
                    pair_score, nutrition_pair_score, rank, reasons,
                    fruit_snapshot
                ) VALUES (
                    :recommendation_id, :fruit_id, 0.7, 0.7,
                    0.75, 0.6, 2, '[]', '{}'
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
                            recommendation_id, fruit_id, score, individual_score,
                            pair_score, nutrition_pair_score, rank, reasons,
                            fruit_snapshot
                        ) VALUES (
                            :recommendation_id, :fruit_id, 0.6, 0.6,
                            0.7, 0.5, 2, '[]', '{}'
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
