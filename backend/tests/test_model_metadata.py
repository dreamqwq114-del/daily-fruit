from collections.abc import Iterable

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Numeric,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import Base


EXPECTED_TABLES = {
    "public.users",
    "public.fruits",
    "public.fruit_facts",
    "public.fruit_nutritions",
    "public.fruit_seasons",
    "public.user_fruit_preferences",
    "public.recommendations",
    "public.recommendation_items",
    "public.recommendation_feedback",
    "public.product_feedback",
    "public.fruit_selection_options",
    "public.user_fruit_option_preferences",
}
EXPECTED_EXTERNAL_TABLES = {"auth.users"}


def business_tables() -> list[Table]:
    return [
        target
        for target in Base.metadata.tables.values()
        if target.info.get("external") is not True
    ]


def table(name: str) -> Table:
    return Base.metadata.tables[f"public.{name}"]


def constraint_names(
    target: Table,
    constraint_type: type[CheckConstraint]
    | type[UniqueConstraint]
    | type[ForeignKeyConstraint],
) -> set[str]:
    return {
        constraint.name
        for constraint in target.constraints
        if isinstance(constraint, constraint_type)
        and constraint.name is not None
    }


def unique_column_sets(target: Table) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in target.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def index_expression_names(index: Index) -> tuple[str, ...]:
    names: list[str] = []
    for expression in index.expressions:
        column = getattr(expression, "element", expression)
        names.append(column.name)
    return tuple(names)


def indexed_leftmost_columns(target: Table) -> set[str]:
    columns = {
        tuple(column.name for column in constraint.columns)[0]
        for constraint in target.constraints
        if isinstance(constraint, UniqueConstraint)
        and constraint.columns
    }
    columns.update(
        index_expression_names(index)[0]
        for index in target.indexes
        if index.expressions
    )
    columns.update(column.name for column in target.primary_key.columns)
    return columns


def check_sql(target: Table) -> dict[str, str]:
    return {
        constraint.name: str(constraint.sqltext)
        for constraint in target.constraints
        if isinstance(constraint, CheckConstraint)
        and constraint.name is not None
    }


def assert_numeric(
    target: Table,
    column_names: Iterable[str],
    precision: int,
    scale: int,
) -> None:
    for column_name in column_names:
        column_type = target.c[column_name].type
        assert isinstance(column_type, Numeric)
        assert column_type.precision == precision
        assert column_type.scale == scale


def test_metadata_contains_expected_public_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES | EXPECTED_EXTERNAL_TABLES
    assert {target.schema for target in business_tables()} == {"public"}
    assert Base.metadata.tables["auth.users"].info["external"] is True


def test_all_orm_relationships_configure_without_database_connection() -> None:
    configure_mappers()


def test_all_primary_keys_are_bigint_identity() -> None:
    for target in business_tables():
        identifier = target.c.id
        assert identifier.primary_key
        assert isinstance(identifier.type, BigInteger)
        assert identifier.identity is not None
        assert identifier.identity.always is False


def test_time_columns_are_timezone_aware_and_have_server_defaults() -> None:
    for target in business_tables():
        created_at = target.c.created_at
        assert isinstance(created_at.type, DateTime)
        assert created_at.type.timezone is True
        assert created_at.nullable is False
        assert created_at.server_default is not None

    for name in (
        "users",
        "fruits",
        "fruit_nutritions",
        "user_fruit_preferences",
    ):
        updated_at = table(name).c.updated_at
        assert isinstance(updated_at.type, DateTime)
        assert updated_at.type.timezone is True
        assert updated_at.nullable is False
        assert updated_at.server_default is not None


def test_user_and_fruit_score_types_and_checks() -> None:
    users = table("users")
    assert_numeric(
        users,
        (
            "sweet_preference",
            "sour_preference",
            "soft_preference",
            "crisp_preference",
            "convenience_preference",
        ),
        4,
        3,
    )
    assert users.c.consumption_horizon_days.server_default is not None
    assert users.c.consumption_horizon_days.nullable is False
    assert users.c.market_access_level.server_default is not None
    assert users.c.market_access_level.nullable is False
    assert users.c.accepts_online_purchase.server_default is not None
    assert users.c.accepts_online_purchase.nullable is False
    assert "ck_users_consumption_horizon_days_values" in check_sql(users)
    assert "ck_users_market_access_level_range" in check_sql(users)
    assert len(check_sql(users)) == 12

    fruits = table("fruits")
    assert_numeric(
        fruits,
        (
            "sweet_score",
            "sour_score",
            "soft_score",
            "crisp_score",
            "convenience_score",
        ),
        4,
        3,
    )
    assert unique_column_sets(fruits) == {("name",), ("code",)}
    assert len(check_sql(fruits)) == 20
    assert fruits.c.is_active.server_default is not None


def test_nutrition_and_season_constraints_match_design() -> None:
    nutritions = table("fruit_nutritions")
    assert unique_column_sets(nutritions) == {("fruit_id",)}
    assert_numeric(
        nutritions,
        (
            "energy",
            "vitamin_c",
            "fiber",
            "potassium",
            "folate",
            "carotenoids",
        ),
        10,
        2,
    )
    assert len(check_sql(nutritions)) == 6

    seasons = table("fruit_seasons")
    assert unique_column_sets(seasons) == {
        ("fruit_id", "data_scope", "region", "start_month", "end_month")
    }
    assert set(check_sql(seasons)) == {
        "ck_fruit_seasons_start_month_range",
        "ck_fruit_seasons_end_month_range",
        "ck_fruit_seasons_score_range",
        "ck_fruit_seasons_region_level_values",
        "ck_fruit_seasons_availability_score_range",
        "ck_fruit_seasons_supply_status_values",
        "ck_fruit_seasons_data_scope_values",
        "ck_fruit_seasons_data_quality_values",
        "ck_fruit_seasons_cultivation_type_values",
        "ck_fruit_seasons_source_year_range",
        "ck_fruit_seasons_source_note_length",
        "ck_fruit_seasons_region_level_contract",
        "ck_fruit_seasons_scoring_evidence",
        "ck_fruit_seasons_legacy_disabled",
        "ck_fruit_seasons_unverified_supply",
        "ck_fruit_seasons_scope_semantics",
    }
    assert {
        index.name: index_expression_names(index)
        for index in seasons.indexes
    } == {
        "ix_fruit_seasons_region_fruit_id": ("region", "fruit_id")
    }


def test_fruit_fact_constraints_and_types_match_design() -> None:
    facts = table("fruit_facts")
    assert unique_column_sets(facts) == {("fruit_id", "sort_order")}
    assert facts.c.sort_order.nullable is False
    assert facts.c.is_active.server_default is not None
    assert set(check_sql(facts)) == {
        "ck_fruit_facts_sort_order_positive",
        "ck_fruit_facts_fact_type_not_blank",
        "ck_fruit_facts_fact_text_not_blank",
    }
    assert {
        index.name: index_expression_names(index)
        for index in facts.indexes
    } == {"ix_fruit_facts_fruit_active": ("fruit_id", "is_active")}


def test_preference_recommendation_and_feedback_constraints() -> None:
    preferences = table("user_fruit_preferences")
    assert unique_column_sets(preferences) == {("user_id", "fruit_id")}
    assert "ck_user_fruit_preferences_score_range" in check_sql(preferences)
    score_constraint = next(
        constraint.sqltext.text
        for constraint in preferences.constraints
        if constraint.name == "ck_user_fruit_preferences_score_range"
    )
    assert "IN (-1, 0, 1, 2)" in score_constraint
    willingness_constraint = next(
        constraint.sqltext.text
        for constraint in preferences.constraints
        if constraint.name == "ck_user_fruit_preferences_willingness_state"
    )
    assert "willing_to_try IS NULL OR has_tried IS FALSE" in willingness_constraint
    assert preferences.c.preference_score.nullable is True
    assert preferences.c.has_tried.nullable is True
    assert preferences.c.willing_to_try.nullable is True

    options = table("fruit_selection_options")
    assert isinstance(options.c.legacy_score_snapshot.type, JSONB)
    assert "ck_fruit_selection_options_ripe_storage_values" in check_sql(options)
    assert (
        "ck_fruit_selection_options_legacy_score_snapshot_object"
        in check_sql(options)
    )

    recommendations = table("recommendations")
    assert unique_column_sets(recommendations) == {
        ("user_id", "recommendation_date", "refresh_number")
    }
    assert set(check_sql(recommendations)) == {
        "ck_recommendations_refresh_number_nonnegative",
        "ck_recommendations_total_score_range",
        "ck_recommendations_status_values",
    }

    items = table("recommendation_items")
    assert unique_column_sets(items) == {
        ("recommendation_id", "rank"),
        ("recommendation_id", "fruit_id"),
    }
    assert isinstance(items.c.reasons.type, JSONB)
    assert items.c.reasons.server_default is not None
    assert "ck_recommendation_items_reasons_array" in check_sql(items)
    assert "ck_recommendation_items_individual_score_range" in check_sql(items)
    assert "ck_recommendation_items_pair_score_range" in check_sql(items)
    assert "ck_recommendation_items_nutrition_pair_score_range" in check_sql(items)
    assert "selection_option_id" in items.c
    assert "selection_option_name_snapshot" in items.c
    assert isinstance(items.c.fruit_snapshot.type, JSONB)
    assert items.c.fruit_snapshot.nullable is False
    assert isinstance(items.c.daily_fact_snapshot.type, JSONB)
    assert "ck_recommendation_items_fruit_snapshot_object" in check_sql(items)
    assert "ck_recommendation_items_daily_fact_snapshot_object" in check_sql(items)

    feedback = table("recommendation_feedback")
    assert unique_column_sets(feedback) == {
        ("recommendation_item_id", "user_id", "feedback_type")
    }
    assert "ck_recommendation_feedback_type_values" in check_sql(feedback)

    product_feedback = table("product_feedback")
    assert set(check_sql(product_feedback)) == {
        "ck_product_feedback_category_values",
        "ck_product_feedback_content_length",
        "ck_product_feedback_page_key_values",
        "ck_product_feedback_status_values",
        "ck_product_feedback_status_resolved_at_consistency",
    }
    assert product_feedback.c.user_id.nullable is True
    assert product_feedback.c.resolved_at.nullable is True
    assert product_feedback.c.status.server_default is not None
    assert {
        index.name: index_expression_names(index)
        for index in product_feedback.indexes
    } == {
        "ix_product_feedback_status_created_at": (
            "status",
            "created_at",
        ),
        "ix_product_feedback_user_id": ("user_id",),
    }


def test_foreign_key_delete_rules_are_explicit() -> None:
    expected = {
        ("fruit_nutritions", "fruit_id"): ("public.fruits.id", "CASCADE"),
        ("fruit_seasons", "fruit_id"): ("public.fruits.id", "CASCADE"),
        ("fruit_facts", "fruit_id"): ("public.fruits.id", "CASCADE"),
        ("user_fruit_preferences", "user_id"): (
            "public.users.id",
            "CASCADE",
        ),
        ("user_fruit_preferences", "fruit_id"): (
            "public.fruits.id",
            "RESTRICT",
        ),
        ("recommendations", "user_id"): ("public.users.id", "RESTRICT"),
        ("recommendation_items", "recommendation_id"): (
            "public.recommendations.id",
            "CASCADE",
        ),
        ("recommendation_items", "fruit_id"): (
            "public.fruits.id",
            "RESTRICT",
        ),
        ("recommendation_feedback", "recommendation_item_id"): (
            "public.recommendation_items.id",
            "CASCADE",
        ),
        ("recommendation_feedback", "user_id"): (
            "public.users.id",
            "RESTRICT",
        ),
        ("users", "auth_user_id"): ("auth.users.id", "SET NULL"),
        ("product_feedback", "user_id"): (
            "public.users.id",
            "SET NULL",
        ),
        ("fruit_selection_options", "fruit_id"): (
            "public.fruits.id",
            "RESTRICT",
        ),
        ("user_fruit_option_preferences", "user_id"): (
            "public.users.id",
            "CASCADE",
        ),
        ("user_fruit_option_preferences", "fruit_id"): (
            "public.fruit_selection_options.fruit_id",
            "RESTRICT",
        ),
        ("user_fruit_option_preferences", "option_id"): (
            "public.fruit_selection_options.id",
            "RESTRICT",
        ),
        ("recommendation_items", "selection_option_id"): (
            "public.fruit_selection_options.id",
            "RESTRICT",
        ),
    }

    actual: dict[tuple[str, str], tuple[str, str | None]] = {}
    for table_name in EXPECTED_TABLES:
        target = Base.metadata.tables[table_name]
        for foreign_key in target.foreign_keys:
            actual[(target.name, foreign_key.parent.name)] = (
                foreign_key.target_fullname,
                foreign_key.ondelete,
            )

    assert actual == expected


def test_every_foreign_key_has_a_leftmost_index_path() -> None:
    for target in business_tables():
        indexed_columns = indexed_leftmost_columns(target)
        for foreign_key in target.foreign_keys:
            assert foreign_key.parent.name in indexed_columns, (
                f"{target.fullname}.{foreign_key.parent.name} lacks "
                "a leftmost index"
            )


def test_recommendation_indexes_support_active_and_history_queries() -> None:
    recommendations = table("recommendations")
    indexes = {index.name: index for index in recommendations.indexes}

    active = indexes["uq_recommendations_active_user_date"]
    assert active.unique is True
    assert index_expression_names(active) == (
        "user_id",
        "recommendation_date",
    )
    assert str(active.dialect_options["postgresql"]["where"]) == (
        "status = 'active'"
    )

    history = indexes["ix_recommendations_user_history"]
    assert index_expression_names(history) == (
        "user_id",
        "recommendation_date",
        "refresh_number",
    )
    compiled = str(CreateIndex(history).compile(dialect=postgresql.dialect()))
    assert "recommendation_date DESC" in compiled
    assert "refresh_number DESC" in compiled


def test_postgresql_ddl_compiles_without_database_connection() -> None:
    dialect = postgresql.dialect()

    table_statements = [
        str(CreateTable(target).compile(dialect=dialect))
        for target in business_tables()
    ]
    index_statements = [
        str(CreateIndex(index).compile(dialect=dialect))
        for target in business_tables()
        for index in target.indexes
    ]
    ddl = "\n".join(table_statements + index_statements)

    assert "GENERATED BY DEFAULT AS IDENTITY" in ddl
    assert "TIMESTAMP WITH TIME ZONE" in ddl
    assert "JSONB DEFAULT '[]'::jsonb NOT NULL" in ddl
    assert "WHERE status = 'active'" in ddl
    assert "CREATE TABLE public.users" in ddl
    assert "FOREIGN KEY(auth_user_id) REFERENCES auth.users" in ddl
    assert "storage." not in ddl
