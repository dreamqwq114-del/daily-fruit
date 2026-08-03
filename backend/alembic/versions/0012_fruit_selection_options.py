"""Add parent-fruit consumption selection options and history snapshots."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OPTION_TABLE = "fruit_selection_options"
_PREFERENCE_TABLE = "user_fruit_option_preferences"


def _set_backend_only_permissions(table: str, sequence: str) -> None:
    """Keep browser roles away from option metadata and user preferences."""

    op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM PUBLIC"))
    op.execute(sa.text(f"REVOKE ALL PRIVILEGES ON SEQUENCE public.{sequence} FROM PUBLIC"))
    for role in ("anon", "authenticated"):
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles "
                f"WHERE rolname = '{role}') THEN "
                f"EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM {role}'; "
                f"EXECUTE 'REVOKE ALL PRIVILEGES ON SEQUENCE public.{sequence} FROM {role}'; "
                "END IF; END $$;"
            )
        )


def upgrade() -> None:
    op.create_table(
        _OPTION_TABLE,
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("fruit_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sweet_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("sour_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("soft_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("crisp_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("data_quality", sa.String(length=20), nullable=False, server_default=sa.text("'low'")),
        sa.Column("data_source_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "sweet_score IS NULL OR sweet_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_sweet_range",
        ),
        sa.CheckConstraint(
            "sour_score IS NULL OR sour_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_sour_range",
        ),
        sa.CheckConstraint(
            "soft_score IS NULL OR soft_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_soft_range",
        ),
        sa.CheckConstraint(
            "crisp_score IS NULL OR crisp_score BETWEEN 0 AND 1",
            name="ck_fruit_selection_options_crisp_range",
        ),
        sa.CheckConstraint(
            "is_default = false OR is_active = true",
            name="ck_fruit_selection_options_default_active",
        ),
        sa.CheckConstraint(
            "display_order > 0",
            name="ck_fruit_selection_options_display_order_positive",
        ),
        sa.ForeignKeyConstraint(
            ["fruit_id"],
            ["public.fruits.id"],
            name="fk_fruit_selection_options_fruit_id_fruits",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{_OPTION_TABLE}")),
        sa.UniqueConstraint("fruit_id", "code", name="uq_fruit_selection_options_fruit_code"),
        sa.UniqueConstraint("fruit_id", "id", name="uq_fruit_selection_options_fruit_id_id"),
        schema="public",
    )
    op.create_index(
        "uq_fruit_selection_options_active_default",
        _OPTION_TABLE,
        ["fruit_id"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("is_default IS TRUE AND is_active IS TRUE"),
    )
    op.create_index(
        "ix_fruit_selection_options_fruit_active_order",
        _OPTION_TABLE,
        ["fruit_id", "is_active", "display_order"],
        unique=False,
        schema="public",
    )

    op.create_table(
        _PREFERENCE_TABLE,
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("fruit_id", sa.BigInteger(), nullable=False),
        sa.Column("option_id", sa.BigInteger(), nullable=False),
        sa.Column("preference", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "preference IN ('liked', 'disliked')",
            name="ck_user_fruit_option_preferences_preference_values",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="fk_user_fruit_option_preferences_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fruit_id", "option_id"],
            [
                "public.fruit_selection_options.fruit_id",
                "public.fruit_selection_options.id",
            ],
            name="fk_user_fruit_option_preferences_fruit_option",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{_PREFERENCE_TABLE}")),
        sa.UniqueConstraint(
            "user_id", "option_id", name="uq_user_fruit_option_preferences_user_option"
        ),
        schema="public",
    )
    op.create_index(
        "ix_user_fruit_option_preferences_user_fruit",
        _PREFERENCE_TABLE,
        ["user_id", "fruit_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_user_fruit_option_preferences_fruit_id",
        _PREFERENCE_TABLE,
        ["fruit_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_user_fruit_option_preferences_option_id",
        _PREFERENCE_TABLE,
        ["option_id"],
        unique=False,
        schema="public",
    )

    snapshot_columns = (
        sa.Column("selection_option_id", sa.BigInteger(), nullable=True),
        sa.Column("selection_option_name_snapshot", sa.String(length=100), nullable=True),
        sa.Column("selection_option_code_snapshot", sa.String(length=40), nullable=True),
        sa.Column("selection_resolution_source", sa.String(length=40), nullable=True),
        sa.Column("effective_sweet_score_snapshot", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("effective_sour_score_snapshot", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("effective_soft_score_snapshot", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("effective_crisp_score_snapshot", sa.Numeric(precision=4, scale=3), nullable=True),
    )
    for column in snapshot_columns:
        op.add_column("recommendation_items", column, schema="public")
    op.create_foreign_key(
        "fk_recommendation_items_selection_option",
        "recommendation_items",
        _OPTION_TABLE,
        ["selection_option_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_recommendation_items_selection_option_id",
        "recommendation_items",
        ["selection_option_id"],
        unique=False,
        schema="public",
    )
    op.create_check_constraint(
        "ck_recommendation_items_selection_resolution_source",
        "recommendation_items",
        "selection_resolution_source IS NULL OR selection_resolution_source IN "
        "('explicit', 'inferred_from_global_preference', 'default', 'not_applicable')",
        schema="public",
    )
    for name, column in (
        ("sweet", "effective_sweet_score_snapshot"),
        ("sour", "effective_sour_score_snapshot"),
        ("soft", "effective_soft_score_snapshot"),
        ("crisp", "effective_crisp_score_snapshot"),
    ):
        op.create_check_constraint(
            f"ck_recommendation_items_selection_{name}_range",
            "recommendation_items",
            f"{column} IS NULL OR {column} BETWEEN 0 AND 1",
            schema="public",
        )

    _set_backend_only_permissions(_OPTION_TABLE, "fruit_selection_options_id_seq")
    _set_backend_only_permissions(_PREFERENCE_TABLE, "user_fruit_option_preferences_id_seq")


def downgrade() -> None:
    for name in (
        "ck_recommendation_items_selection_crisp_range",
        "ck_recommendation_items_selection_soft_range",
        "ck_recommendation_items_selection_sour_range",
        "ck_recommendation_items_selection_sweet_range",
        "ck_recommendation_items_selection_resolution_source",
    ):
        op.drop_constraint(name, "recommendation_items", schema="public", type_="check")
    op.drop_constraint(
        "fk_recommendation_items_selection_option",
        "recommendation_items",
        schema="public",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_recommendation_items_selection_option_id",
        table_name="recommendation_items",
        schema="public",
    )
    for column in (
        "effective_crisp_score_snapshot",
        "effective_soft_score_snapshot",
        "effective_sour_score_snapshot",
        "effective_sweet_score_snapshot",
        "selection_resolution_source",
        "selection_option_name_snapshot",
        "selection_option_code_snapshot",
        "selection_option_id",
    ):
        op.drop_column("recommendation_items", column, schema="public")

    op.drop_index(
        "ix_user_fruit_option_preferences_user_fruit",
        table_name=_PREFERENCE_TABLE,
        schema="public",
    )
    op.drop_index(
        "ix_user_fruit_option_preferences_fruit_id",
        table_name=_PREFERENCE_TABLE,
        schema="public",
    )
    op.drop_index(
        "ix_user_fruit_option_preferences_option_id",
        table_name=_PREFERENCE_TABLE,
        schema="public",
    )
    op.drop_table(_PREFERENCE_TABLE, schema="public")
    op.drop_index(
        "ix_fruit_selection_options_fruit_active_order",
        table_name=_OPTION_TABLE,
        schema="public",
    )
    op.drop_index(
        "uq_fruit_selection_options_active_default",
        table_name=_OPTION_TABLE,
        schema="public",
    )
    op.drop_table(_OPTION_TABLE, schema="public")
