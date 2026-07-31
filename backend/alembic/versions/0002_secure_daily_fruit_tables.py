"""Secure daily-fruit tables for backend-only access.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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
DATA_API_ROLES = ("anon", "authenticated")


def comma_separated_objects(names: tuple[str, ...]) -> str:
    return ", ".join(f'public."{name}"' for name in names)


def revoke_from_optional_role(role: str) -> None:
    tables = comma_separated_objects(BUSINESS_TABLES)
    sequences = comma_separated_objects(IDENTITY_SEQUENCES)
    op.execute(
        sa.text(
            f"""
            DO $daily_fruit_security$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_catalog.pg_roles
                    WHERE rolname = '{role}'
                ) THEN
                    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE {tables} FROM {role}';
                    EXECUTE 'REVOKE ALL PRIVILEGES ON SEQUENCE {sequences} FROM {role}';
                END IF;
            END
            $daily_fruit_security$;
            """
        )
    )


def secure_known_rls_helper() -> None:
    op.execute(
        sa.text(
            """
            DO $daily_fruit_security$
            BEGIN
                IF to_regprocedure('public.rls_auto_enable()') IS NOT NULL THEN
                    REVOKE EXECUTE ON FUNCTION public.rls_auto_enable()
                        FROM PUBLIC;
                    IF EXISTS (
                        SELECT 1 FROM pg_catalog.pg_roles
                        WHERE rolname = 'anon'
                    ) THEN
                        REVOKE EXECUTE ON FUNCTION public.rls_auto_enable()
                            FROM anon;
                    END IF;
                    IF EXISTS (
                        SELECT 1 FROM pg_catalog.pg_roles
                        WHERE rolname = 'authenticated'
                    ) THEN
                        REVOKE EXECUTE ON FUNCTION public.rls_auto_enable()
                            FROM authenticated;
                    END IF;
                END IF;
            END
            $daily_fruit_security$;
            """
        )
    )


def upgrade() -> None:
    """Deny browser roles and enable RLS without allow policies."""
    for table_name in BUSINESS_TABLES:
        op.execute(
            sa.text(
                f'ALTER TABLE public."{table_name}" '
                "ENABLE ROW LEVEL SECURITY"
            )
        )

    op.execute(
        sa.text(
            "REVOKE ALL PRIVILEGES ON "
            f"TABLE {comma_separated_objects(BUSINESS_TABLES)} "
            "FROM PUBLIC"
        )
    )
    op.execute(
        sa.text(
            "REVOKE ALL PRIVILEGES ON "
            f"SEQUENCE {comma_separated_objects(IDENTITY_SEQUENCES)} "
            "FROM PUBLIC"
        )
    )
    for role in DATA_API_ROLES:
        revoke_from_optional_role(role)

    secure_known_rls_helper()


def downgrade() -> None:
    """Disable RLS only; never re-grant revoked browser privileges."""
    for table_name in reversed(BUSINESS_TABLES):
        op.execute(
            sa.text(
                f'ALTER TABLE public."{table_name}" '
                "DISABLE ROW LEVEL SECURITY"
            )
        )

    # Privilege revocations and the SECURITY DEFINER function hardening are
    # intentionally retained because a downgrade must not broaden access.
