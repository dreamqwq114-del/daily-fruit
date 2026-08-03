"""Create backend-only product feedback persistence.

The table is deliberately separate from recommendation_feedback.  It stores
only authenticated product suggestions and issue reports; operators review
and resolve rows manually through the Supabase SQL Editor.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the constrained, backend-only feedback table."""

    op.create_table(
        "product_feedback",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("content", sa.String(length=1000), nullable=False),
        sa.Column("page_key", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'new'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "category IN ("
            "'recommendation_quality', 'suggestion', 'bug', "
            "'fruit_content', 'other'"
            ")",
            name="ck_product_feedback_category_values",
        ),
        sa.CheckConstraint(
            "char_length(btrim(content)) BETWEEN 1 AND 1000",
            name="ck_product_feedback_content_length",
        ),
        sa.CheckConstraint(
            "page_key IS NULL OR page_key IN "
            "('today', 'preferences', 'history')",
            name="ck_product_feedback_page_key_values",
        ),
        sa.CheckConstraint(
            "status IN ('new', 'resolved')",
            name="ck_product_feedback_status_values",
        ),
        sa.CheckConstraint(
            "(status = 'new' AND resolved_at IS NULL) OR "
            "(status = 'resolved' AND resolved_at IS NOT NULL)",
            name="ck_product_feedback_status_resolved_at_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="fk_product_feedback_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_feedback")),
        schema="public",
    )
    op.create_index(
        "ix_product_feedback_status_created_at",
        "product_feedback",
        ["status", sa.literal_column("created_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_product_feedback_user_id",
        "product_feedback",
        ["user_id"],
        unique=False,
        schema="public",
    )

    # Match the existing backend-only posture for every public business table.
    op.execute(
        sa.text(
            "ALTER TABLE public.product_feedback "
            "ENABLE ROW LEVEL SECURITY"
        )
    )
    op.execute(
        sa.text(
            "REVOKE ALL PRIVILEGES ON TABLE public.product_feedback "
            "FROM PUBLIC"
        )
    )
    op.execute(
        sa.text(
            "REVOKE ALL PRIVILEGES ON SEQUENCE "
            "public.product_feedback_id_seq FROM PUBLIC"
        )
    )
    for role in ("anon", "authenticated"):
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles "
                f"WHERE rolname = '{role}') THEN "
                f"EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE "
                f"public.product_feedback FROM {role}'; "
                f"EXECUTE 'REVOKE ALL PRIVILEGES ON SEQUENCE "
                f"public.product_feedback_id_seq FROM {role}'; "
                "END IF; END $$;"
            )
        )


def downgrade() -> None:
    """Drop only objects created by this migration."""

    op.drop_index(
        "ix_product_feedback_user_id",
        table_name="product_feedback",
        schema="public",
    )
    op.drop_index(
        "ix_product_feedback_status_created_at",
        table_name="product_feedback",
        schema="public",
    )
    op.drop_table("product_feedback", schema="public")
