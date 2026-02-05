"""Add optimization indexes for common query patterns.

Revision ID: 026
Revises: 025
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes for better query performance."""
    # Create indexes idempotently using IF NOT EXISTS

    # License last_activity_at for inactive license reports
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_licenses_last_activity_at
        ON licenses (last_activity_at)
    """)

    # License created_at for time-range report filtering
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_licenses_created_at
        ON licenses (created_at DESC)
    """)

    # Employee department for department-based filtering
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_employees_department
        ON employees (department)
    """)

    # Composite index for provider + license_type queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_licenses_provider_license_type
        ON licenses (provider_id, license_type)
    """)

    # Index for license status filtering
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_licenses_status
        ON licenses (status)
    """)

    # Index for suggested employee matching queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_licenses_suggested_employee
        ON licenses (suggested_employee_id)
        WHERE suggested_employee_id IS NOT NULL
    """)

    # Index for match_reviewed_at for sync optimization
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_licenses_match_reviewed_at
        ON licenses (match_reviewed_at)
        WHERE match_reviewed_at IS NOT NULL
    """)


def downgrade() -> None:
    """Remove the optimization indexes."""
    op.execute("DROP INDEX IF EXISTS ix_licenses_last_activity_at")
    op.execute("DROP INDEX IF EXISTS ix_licenses_created_at")
    op.execute("DROP INDEX IF EXISTS ix_employees_department")
    op.execute("DROP INDEX IF EXISTS ix_licenses_provider_license_type")
    op.execute("DROP INDEX IF EXISTS ix_licenses_status")
    op.execute("DROP INDEX IF EXISTS ix_licenses_suggested_employee")
    op.execute("DROP INDEX IF EXISTS ix_licenses_match_reviewed_at")
