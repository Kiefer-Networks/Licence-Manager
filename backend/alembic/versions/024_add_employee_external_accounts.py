"""Add employee external accounts table.

Revision ID: 024
Revises: 023
Create Date: 2026-02-05

This migration adds support for linking external provider usernames to employees:
- employee_external_accounts: Maps provider usernames to employees
- Enables matching licenses to employees when providers don't return emails
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add employee_external_accounts table."""
    op.create_table(
        "employee_external_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "employee_id",
            UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_type", sa.String(100), nullable=False),
        sa.Column("external_username", sa.String(255), nullable=False),
        sa.Column("external_user_id", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("linked_by_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create unique constraint for provider_type + external_username
    op.create_unique_constraint(
        "uq_employee_external_accounts_provider_username",
        "employee_external_accounts",
        ["provider_type", "external_username"],
    )

    # Create index for employee lookup
    op.create_index(
        "ix_employee_external_accounts_employee_id",
        "employee_external_accounts",
        ["employee_id"],
    )

    # Create index for provider type lookup
    op.create_index(
        "ix_employee_external_accounts_provider_type",
        "employee_external_accounts",
        ["provider_type"],
    )

    # Create index for username lookup
    op.create_index(
        "ix_employee_external_accounts_external_username",
        "employee_external_accounts",
        ["external_username"],
    )


def downgrade() -> None:
    """Remove employee_external_accounts table."""
    op.drop_index(
        "ix_employee_external_accounts_external_username",
        table_name="employee_external_accounts",
    )
    op.drop_index(
        "ix_employee_external_accounts_provider_type",
        table_name="employee_external_accounts",
    )
    op.drop_index(
        "ix_employee_external_accounts_employee_id",
        table_name="employee_external_accounts",
    )
    op.drop_constraint(
        "uq_employee_external_accounts_provider_username",
        "employee_external_accounts",
        type_="unique",
    )
    op.drop_table("employee_external_accounts")
