"""Add additional query indexes for common filter combinations.

Revision ID: 016
Revises: 015
Create Date: 2026-01-31

This migration adds indexes to improve query performance for:
- Composite license filtering (provider_id, employee_id, status)
- License match_status queries
- Provider payment_method lookups
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add additional query indexes."""
    # Composite index for common license filter combinations
    # Supports queries filtering by provider + employee + status
    op.create_index(
        "ix_licenses_provider_employee_status",
        "licenses",
        ["provider_id", "employee_id", "status"],
        unique=False,
    )

    # Index for match_status filtering (not covered by partial index)
    op.create_index(
        "ix_licenses_match_status",
        "licenses",
        ["match_status"],
        unique=False,
    )

    # Index for provider payment_method FK lookups
    op.create_index(
        "ix_providers_payment_method_id",
        "providers",
        ["payment_method_id"],
        unique=False,
    )

    # Index for license type queries (common filter)
    op.create_index(
        "ix_licenses_license_type",
        "licenses",
        ["license_type"],
        unique=False,
    )

    # Partial index for active service accounts (common dashboard query)
    op.execute(
        """
        CREATE INDEX ix_licenses_active_service_accounts
        ON licenses (provider_id, service_account_owner_id)
        WHERE is_service_account = true AND status = 'active'
        """
    )


def downgrade() -> None:
    """Remove additional query indexes."""
    op.execute("DROP INDEX IF EXISTS ix_licenses_active_service_accounts")
    op.drop_index("ix_licenses_license_type", table_name="licenses")
    op.drop_index("ix_providers_payment_method_id", table_name="providers")
    op.drop_index("ix_licenses_match_status", table_name="licenses")
    op.drop_index("ix_licenses_provider_employee_status", table_name="licenses")
