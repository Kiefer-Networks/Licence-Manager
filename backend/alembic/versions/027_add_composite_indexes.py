"""Add composite indexes for query optimization.

Revision ID: 027
Revises: 026
Create Date: 2026-02-06

This migration adds composite indexes identified during the performance audit:
1. Composite index for active licenses per provider (provider_id, status, employee_id)
2. Composite index for match status queries (match_status, employee_id, status)
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add composite indexes for query optimization."""
    # Create composite index for "active licenses per provider" queries
    # This optimizes dashboard and report queries that filter by provider and status
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_licenses_provider_status_employee
        ON licenses(provider_id, status, employee_id DESC NULLS LAST)
        WHERE status = 'active'
    """)

    # Create composite index for match status queries during sync
    # This optimizes queries that filter by match_status and employee assignment
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_licenses_match_status_employee_status
        ON licenses(match_status, employee_id, status)
        WHERE status = 'active'
    """)


def downgrade() -> None:
    """Remove composite indexes."""
    op.execute("DROP INDEX IF EXISTS ix_licenses_provider_status_employee")
    op.execute("DROP INDEX IF EXISTS ix_licenses_match_status_employee_status")
