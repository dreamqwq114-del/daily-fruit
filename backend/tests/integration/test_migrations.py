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
from app.seed.seed_fruits import load_seed_dataset, seed_database


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

DISPOSABLE_DATA_DELETE_ORDER = (
    "recommendation_feedback",
    "recommendation_items",
    "recommendations",
    "user_fruit_option_preferences",
    "user_fruit_preferences",
    "fruit_selection_options",
    "fruit_facts",
    "fruit_seasons",
    "fruit_nutritions",
    "product_feedback",
    "users",
    "fruits",
)


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


def clear_disposable_database_data(engine: Engine) -> None:
    """Remove only known fixture data before testing migration round trips."""

    with engine.begin() as connection:
        public_tables = set(
            inspect(connection).get_table_names(schema="public")
        )
        for table_name in DISPOSABLE_DATA_DELETE_ORDER:
            if table_name in public_tables:
                connection.execute(text(f"DELETE FROM public.{table_name}"))

        auth_tables = set(inspect(connection).get_table_names(schema="auth"))
        if "users" in auth_tables:
            connection.execute(text("DELETE FROM auth.users"))


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
    if settings.test_database_url != database_url:
        raise RuntimeError("refusing an unresolved destructive test database")
    parsed = urlsplit(database_url)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("destructive migration tests require localhost")
    if parsed.path.strip("/") != "daily_fruit_test":
        raise RuntimeError(
            "destructive migration tests require daily_fruit_test"
        )

    engine = create_engine(database_url, poolclass=NullPool)
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "auth" not in inspector.get_schema_names():
            connection.execute(text("CREATE SCHEMA auth"))
        auth_tables = set(inspect(connection).get_table_names(schema="auth"))
        if not auth_tables <= {"users"}:
            raise RuntimeError(
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
    if unknown:
        raise RuntimeError(f"refusing to alter unknown test tables: {unknown}")

    clear_disposable_database_data(engine)
    run_alembic("downgrade", "base", database_url=database_url)
    run_alembic("upgrade", "0001", database_url=database_url)
    try:
        yield engine, database_url
    finally:
        try:
            clear_disposable_database_data(engine)
            run_alembic("downgrade", "base", database_url=database_url)
            run_alembic("upgrade", "head", database_url=database_url)
            seed_database(engine, load_seed_dataset())
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
    # Keep this test independent from whichever migration state a previous
    # module test left behind.
    run_alembic("downgrade", "base", database_url=database_url)
    run_alembic("upgrade", "0001", database_url=database_url)
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
        ).scalar_one() == "0015"
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


def test_0014_refuses_invalid_history_without_rewriting_rows(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, database_url = migrated_database
    run_alembic("upgrade", "head", database_url=database_url)
    run_alembic("downgrade", "0013", database_url=database_url)
    with engine.begin() as connection:
        user_id = insert_user(connection)
        fruit_id = insert_fruit(connection, "0014-invalid-history")
        connection.execute(
            text(
                """
                INSERT INTO public.user_fruit_preferences (
                    user_id, fruit_id, preference_score, is_forbidden
                ) VALUES (:user_id, :fruit_id, -0.50, false)
                """
            ),
            {"user_id": user_id, "fruit_id": fruit_id},
        )

    fractional = invoke_alembic("upgrade", "head", database_url=database_url)
    assert fractional.returncode != 0
    assert "non-discrete rows require an explicit data decision" in (
        fractional.stdout + fractional.stderr
    )
    with engine.begin() as connection:
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0013"
        assert connection.execute(
            text(
                "SELECT preference_score FROM public.user_fruit_preferences "
                "WHERE user_id=:user_id AND fruit_id=:fruit_id"
            ),
            {"user_id": user_id, "fruit_id": fruit_id},
        ).scalar_one() == pytest.approx(-0.5)
        connection.execute(
            text(
                "UPDATE public.user_fruit_preferences "
                "SET preference_score=0, has_tried=true, willing_to_try=false "
                "WHERE user_id=:user_id AND fruit_id=:fruit_id"
            ),
            {"user_id": user_id, "fruit_id": fruit_id},
        )

    willingness = invoke_alembic("upgrade", "head", database_url=database_url)
    assert willingness.returncode != 0
    assert "contradictory rows require an explicit data decision" in (
        willingness.stdout + willingness.stderr
    )
    with engine.begin() as connection:
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0013"
        assert connection.execute(
            text(
                "SELECT willing_to_try FROM public.user_fruit_preferences "
                "WHERE user_id=:user_id AND fruit_id=:fruit_id"
            ),
            {"user_id": user_id, "fruit_id": fruit_id},
        ).scalar_one() is False
        connection.execute(
            text(
                "UPDATE public.user_fruit_preferences SET willing_to_try=NULL "
                "WHERE user_id=:user_id AND fruit_id=:fruit_id"
            ),
            {"user_id": user_id, "fruit_id": fruit_id},
        )

    run_alembic("upgrade", "head", database_url=database_url)
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM public.users WHERE id=:user_id"),
            {"user_id": user_id},
        )
        connection.execute(
            text("DELETE FROM public.fruits WHERE id=:fruit_id"),
            {"fruit_id": fruit_id},
        )


def test_0015_preserves_legacy_rows_and_rejects_invalid_region_transactionally(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, database_url = migrated_database
    run_alembic("upgrade", "head", database_url=database_url)
    run_alembic("downgrade", "0014", database_url=database_url)
    with engine.begin() as connection:
        fruit_id = insert_fruit(connection, "0015-legacy-season")
        legacy_row = connection.execute(
            text(
                """
                INSERT INTO public.fruit_seasons (
                    fruit_id, region, region_level, start_month, end_month,
                    season_score, availability_score, supply_status
                ) VALUES (
                    :fruit_id, '全国', 'area', 9, 11, 0.82, 0.61, 'available'
                )
                RETURNING id, created_at
                """
            ),
            {"fruit_id": fruit_id},
        ).one()

    failed = invoke_alembic("upgrade", "head", database_url=database_url)
    assert failed.returncode != 0
    assert "explicit region-level decision" in failed.stdout + failed.stderr
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0014"
        assert "data_scope" not in {
            column["name"]
            for column in inspect(connection).get_columns(
                "fruit_seasons", schema="public"
            )
        }
        assert connection.execute(
            text("SELECT count(*) FROM public.fruit_seasons WHERE id=:id"),
            {"id": legacy_row.id},
        ).scalar_one() == 1

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE public.fruit_seasons SET region_level='national' "
                "WHERE id=:id"
            ),
            {"id": legacy_row.id},
        )
    run_alembic("upgrade", "head", database_url=database_url)
    with engine.connect() as connection:
        migrated = connection.execute(
            text(
                """
                SELECT id, created_at, season_score, availability_score,
                       supply_status, data_scope, data_quality,
                       is_scoring_enabled
                FROM public.fruit_seasons WHERE id=:id
                """
            ),
            {"id": legacy_row.id},
        ).mappings().one()
        assert migrated["id"] == legacy_row.id
        assert migrated["created_at"] == legacy_row.created_at
        assert float(migrated["season_score"]) == pytest.approx(0.82)
        assert float(migrated["availability_score"]) == pytest.approx(0.61)
        assert migrated["supply_status"] == "available"
        assert migrated["data_scope"] == "legacy"
        assert migrated["data_quality"] == "unverified"
        assert migrated["is_scoring_enabled"] is False

    run_alembic("downgrade", "0014", database_url=database_url)
    with engine.connect() as connection:
        restored = connection.execute(
            text(
                """
                SELECT id, created_at, season_score, availability_score,
                       supply_status, region_level
                FROM public.fruit_seasons WHERE id=:id
                """
            ),
            {"id": legacy_row.id},
        ).mappings().one()
        assert restored["id"] == legacy_row.id
        assert restored["created_at"] == legacy_row.created_at
        assert float(restored["season_score"]) == pytest.approx(0.82)
        assert float(restored["availability_score"]) == pytest.approx(0.61)
        assert restored["supply_status"] == "available"
        assert restored["region_level"] == "national"

    run_alembic("upgrade", "head", database_url=database_url)
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM public.fruits WHERE id=:id"),
            {"id": fruit_id},
        )


def test_0015_scope_uniqueness_and_downgrade_guard_are_transactional(
    migrated_database: tuple[Engine, str],
) -> None:
    engine, database_url = migrated_database
    run_alembic("upgrade", "head", database_url=database_url)
    with engine.begin() as connection:
        fruit_id = insert_fruit(connection, "0015-evidence-season")
        connection.execute(
            text(
                """
                INSERT INTO public.fruit_seasons (
                    fruit_id, region, region_level, start_month, end_month,
                    season_score, availability_score, supply_status,
                    data_scope, data_quality, cultivation_type,
                    source_note, source_year, is_scoring_enabled
                ) VALUES (
                    :fruit_id, '华东', 'area', 6, 8,
                    0.90, 0.45, 'unknown', 'harvest', 'high',
                    'open_field', 'test harvest evidence', 2026, true
                ), (
                    :fruit_id, '华东', 'area', 6, 8,
                    0.35, 0.70, 'available', 'market', 'medium',
                    'unknown', 'test market evidence', 2026, true
                )
                """
            ),
            {"fruit_id": fruit_id},
        )
        assert connection.execute(
            text(
                "SELECT count(*) FROM public.fruit_seasons "
                "WHERE fruit_id=:fruit_id"
            ),
            {"fruit_id": fruit_id},
        ).scalar_one() == 2
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        INSERT INTO public.fruit_seasons (
                            fruit_id, region, region_level,
                            start_month, end_month, season_score,
                            availability_score, supply_status, data_scope,
                            data_quality, cultivation_type, source_note,
                            source_year, is_scoring_enabled
                        ) VALUES (
                            :fruit_id, '华东', 'area', 6, 8, 0.80,
                            0.45, 'unknown', 'harvest', 'medium',
                            'open_field', 'duplicate evidence', 2026, true
                        )
                        """
                    ),
                    {"fruit_id": fruit_id},
                )

    failed = invoke_alembic("downgrade", "0014", database_url=database_url)
    assert failed.returncode != 0
    assert "without discarding evidence" in failed.stdout + failed.stderr
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0015"
        assert connection.execute(
            text(
                "SELECT count(*) FROM public.fruit_seasons "
                "WHERE fruit_id=:fruit_id"
            ),
            {"fruit_id": fruit_id},
        ).scalar_one() == 2
        assert "data_scope" in {
            column["name"]
            for column in inspect(connection).get_columns(
                "fruit_seasons", schema="public"
            )
        }

    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM public.fruits WHERE id=:id"),
            {"id": fruit_id},
        )


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
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        INSERT INTO public.fruit_seasons (
                            fruit_id, region, region_level,
                            start_month, end_month, season_score,
                            data_scope, data_quality, is_scoring_enabled
                        ) VALUES (
                            :fruit_id, '西北', 'area', 9, 10, 0.9,
                            'harvest', 'high', true
                        )
                        """
                    ),
                    {"fruit_id": fruit_id},
                )
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        INSERT INTO public.fruit_seasons (
                            fruit_id, region, region_level,
                            start_month, end_month, season_score,
                            availability_score, supply_status,
                            data_scope, data_quality, is_scoring_enabled
                        ) VALUES (
                            :fruit_id, '全国', 'national', 1, 12, 0.35,
                            0.9, 'available', 'market', 'unverified', false
                        )
                        """
                    ),
                    {"fruit_id": fruit_id},
                )
        connection.execute(
            text(
                """
                INSERT INTO public.fruit_seasons (
                    fruit_id, region, region_level,
                    start_month, end_month, season_score
                ) VALUES (:fruit_id, '华东', 'area', 12, 4, 0.9)
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
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        INSERT INTO public.user_fruit_preferences (
                            user_id, fruit_id, preference_score, is_forbidden
                        ) VALUES (:user_id, :fruit_id, -0.50, false)
                        """
                    ),
                    {"user_id": user_id, "fruit_id": second_fruit_id},
                )
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        INSERT INTO public.user_fruit_preferences (
                            user_id, fruit_id, preference_score, is_forbidden,
                            has_tried, willing_to_try
                        ) VALUES (:user_id, :fruit_id, 0, false, true, false)
                        """
                    ),
                    {"user_id": user_id, "fruit_id": second_fruit_id},
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
