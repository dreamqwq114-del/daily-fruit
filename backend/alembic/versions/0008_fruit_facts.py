"""Create backend-only daily fruit facts.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create facts and keep the new public table backend-only."""

    op.create_table(
        "fruit_facts",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("fruit_id", sa.BigInteger(), nullable=False),
        sa.Column("fact_type", sa.String(length=40), nullable=False),
        sa.Column("fact_text", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "sort_order > 0",
            name="ck_fruit_facts_sort_order_positive",
        ),
        sa.CheckConstraint(
            "length(btrim(fact_type)) > 0",
            name="ck_fruit_facts_fact_type_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(fact_text)) > 0",
            name="ck_fruit_facts_fact_text_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["fruit_id"],
            ["public.fruits.id"],
            name="fk_fruit_facts_fruit_id_fruits",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fruit_facts")),
        sa.UniqueConstraint(
            "fruit_id",
            "sort_order",
            name="uq_fruit_facts_fruit_sort_order",
        ),
        schema="public",
    )
    op.create_index(
        "ix_fruit_facts_fruit_active",
        "fruit_facts",
        ["fruit_id", "is_active"],
        unique=False,
        schema="public",
    )

    op.execute(
        sa.text(
            "ALTER TABLE public.fruit_facts ENABLE ROW LEVEL SECURITY"
        )
    )
    op.execute(
        sa.text(
            "REVOKE ALL PRIVILEGES ON TABLE public.fruit_facts FROM PUBLIC"
        )
    )
    op.execute(
        sa.text(
            "REVOKE ALL PRIVILEGES ON SEQUENCE public.fruit_facts_id_seq "
            "FROM PUBLIC"
        )
    )
    for role in ("anon", "authenticated"):
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                f"IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles "
                f"WHERE rolname = '{role}') THEN "
                f"EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.fruit_facts "
                f"FROM {role}'; "
                f"EXECUTE 'REVOKE ALL PRIVILEGES ON SEQUENCE "
                f"public.fruit_facts_id_seq FROM {role}'; "
                "END IF; END $$;"
            )
        )


def downgrade() -> None:
    """Drop only the facts table created by this migration."""

    op.drop_index(
        "ix_fruit_facts_fruit_active",
        table_name="fruit_facts",
        schema="public",
    )
    op.drop_table("fruit_facts", schema="public")
