"""Add additional performance indices for common query patterns.

Revision ID: 012
Revises: 011
Create Date: 2026-01-30

This migration adds indices to improve query performance for:
- Service account filtering
- Synced_at sorting
- Employee name search
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add additional performance indices."""
    # Index for service account filtering
    op.create_index(
        "ix_licenses_is_service_account",
        "licenses",
        ["is_service_account"],
        unique=False,
    )

    # Index for synced_at sorting (common sort column)
    op.create_index(
        "ix_licenses_synced_at",
        "licenses",
        ["synced_at"],
        unique=False,
    )

    # Partial index for pending suggestions (faster suggestion queries)
    op.execute(
        """
        CREATE INDEX ix_licenses_pending_suggestions
        ON licenses (match_status, suggested_employee_id)
        WHERE suggested_employee_id IS NOT NULL
        """
    )

    # Index for employee full_name (for name search and fuzzy matching)
    op.create_index(
        "ix_employees_full_name",
        "employees",
        ["full_name"],
        unique=False,
    )

    # GIN index for trigram-based fuzzy name matching (if extension available)
    # This enables fast ILIKE and similarity() queries
    # First try to create the extension, then the index
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_employees_full_name_trgm
            ON employees USING gin (full_name gin_trgm_ops)
            """
        )
    except Exception:
        # Extension not available (e.g., insufficient privileges)
        # The index is optional for performance, skip it
        pass


def downgrade() -> None:
    """Remove additional performance indices."""
    op.execute("DROP INDEX IF EXISTS ix_employees_full_name_trgm")
    op.drop_index("ix_employees_full_name", table_name="employees")
    op.execute("DROP INDEX IF EXISTS ix_licenses_pending_suggestions")
    op.drop_index("ix_licenses_synced_at", table_name="licenses")
    op.drop_index("ix_licenses_is_service_account", table_name="licenses")
