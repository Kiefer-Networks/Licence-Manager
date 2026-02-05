"""Add indexes for account owner lookups and employee fields.

Revision ID: 025
Revises: 024
Create Date: 2026-02-05

This migration adds indexes to improve query performance for:
- Service and admin account owner FK lookups
- Admin account filtering
- Employee hibob_id lookups (used in upserts)
- Employee manager_id lookups
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for account owner lookups."""
    # Index for service account owner FK lookups
    op.create_index(
        "ix_licenses_service_account_owner_id",
        "licenses",
        ["service_account_owner_id"],
        unique=False,
    )

    # Index for admin account owner FK lookups
    op.create_index(
        "ix_licenses_admin_account_owner_id",
        "licenses",
        ["admin_account_owner_id"],
        unique=False,
    )

    # Index for admin account filtering (matching is_service_account index)
    op.create_index(
        "ix_licenses_is_admin_account",
        "licenses",
        ["is_admin_account"],
        unique=False,
    )

    # Partial index for active admin accounts (common dashboard query)
    op.execute(
        """
        CREATE INDEX ix_licenses_active_admin_accounts
        ON licenses (provider_id, admin_account_owner_id)
        WHERE is_admin_account = true AND status = 'active'
        """
    )

    # Index for employee hibob_id lookups (used in upsert during sync)
    op.create_index(
        "ix_employees_hibob_id",
        "employees",
        ["hibob_id"],
        unique=False,
    )

    # Index for employee manager_id FK lookups
    op.create_index(
        "ix_employees_manager_id",
        "employees",
        ["manager_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove account owner indexes."""
    op.drop_index("ix_employees_manager_id", table_name="employees")
    op.drop_index("ix_employees_hibob_id", table_name="employees")
    op.execute("DROP INDEX IF EXISTS ix_licenses_active_admin_accounts")
    op.drop_index("ix_licenses_is_admin_account", table_name="licenses")
    op.drop_index("ix_licenses_admin_account_owner_id", table_name="licenses")
    op.drop_index("ix_licenses_service_account_owner_id", table_name="licenses")
