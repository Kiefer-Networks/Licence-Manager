"""Add performance indexes for frequently queried columns.

Revision ID: 006_add_performance_indexes
Revises: 005_add_cascade_delete_to_licenses
Create Date: 2026-01-30

This migration adds indexes to improve query performance for:
- License searches and filtering
- Employee lookups and filtering
- Provider status queries
- Audit log queries
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes."""
    # License table indexes
    op.create_index(
        "ix_licenses_external_user_id",
        "licenses",
        ["external_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_licenses_status",
        "licenses",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_licenses_provider_id_status",
        "licenses",
        ["provider_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_licenses_employee_id",
        "licenses",
        ["employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_licenses_last_activity_at",
        "licenses",
        ["last_activity_at"],
        unique=False,
    )
    # Partial index for unassigned licenses (employee_id IS NULL)
    op.execute(
        """
        CREATE INDEX ix_licenses_unassigned
        ON licenses (provider_id, status)
        WHERE employee_id IS NULL
        """
    )
    # Index for external email detection (emails with @)
    op.execute(
        """
        CREATE INDEX ix_licenses_external_email
        ON licenses (provider_id)
        WHERE external_user_id LIKE '%@%'
        """
    )

    # Employee table indexes
    op.create_index(
        "ix_employees_department",
        "employees",
        ["department"],
        unique=False,
    )
    op.create_index(
        "ix_employees_status",
        "employees",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_employees_email",
        "employees",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_employees_termination_date",
        "employees",
        ["termination_date"],
        unique=False,
    )
    # Partial index for active employees
    op.execute(
        """
        CREATE INDEX ix_employees_active
        ON employees (department, email)
        WHERE status = 'active'
        """
    )
    # Partial index for recently offboarded employees
    op.execute(
        """
        CREATE INDEX ix_employees_offboarded
        ON employees (termination_date)
        WHERE status = 'offboarded'
        """
    )

    # Provider table indexes
    op.create_index(
        "ix_providers_name",
        "providers",
        ["name"],
        unique=True,
    )
    op.create_index(
        "ix_providers_enabled",
        "providers",
        ["enabled"],
        unique=False,
    )

    # Audit log indexes
    op.create_index(
        "ix_audit_logs_created_at",
        "audit_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_resource_type_id",
        "audit_logs",
        ["resource_type", "resource_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_admin_user_id",
        "audit_logs",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action"],
        unique=False,
    )

    # Refresh tokens index for fast lookup
    op.create_index(
        "ix_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_refresh_tokens_user_id",
        "refresh_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_refresh_tokens_expires_at",
        "refresh_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove performance indexes."""
    # Refresh tokens
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")

    # Audit logs
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_admin_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")

    # Providers
    op.drop_index("ix_providers_enabled", table_name="providers")
    op.drop_index("ix_providers_name", table_name="providers")

    # Employees
    op.execute("DROP INDEX IF EXISTS ix_employees_offboarded")
    op.execute("DROP INDEX IF EXISTS ix_employees_active")
    op.drop_index("ix_employees_termination_date", table_name="employees")
    op.drop_index("ix_employees_email", table_name="employees")
    op.drop_index("ix_employees_status", table_name="employees")
    op.drop_index("ix_employees_department", table_name="employees")

    # Licenses
    op.execute("DROP INDEX IF EXISTS ix_licenses_external_email")
    op.execute("DROP INDEX IF EXISTS ix_licenses_unassigned")
    op.drop_index("ix_licenses_last_activity_at", table_name="licenses")
    op.drop_index("ix_licenses_employee_id", table_name="licenses")
    op.drop_index("ix_licenses_provider_id_status", table_name="licenses")
    op.drop_index("ix_licenses_status", table_name="licenses")
    op.drop_index("ix_licenses_external_user_id", table_name="licenses")
