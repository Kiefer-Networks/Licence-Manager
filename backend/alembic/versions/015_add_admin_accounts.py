"""Add admin account support to licenses.

Revision ID: 015
Revises: 014
Create Date: 2025-01-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add admin account columns to licenses table
    op.add_column(
        "licenses",
        sa.Column("is_admin_account", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "licenses",
        sa.Column("admin_account_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "licenses",
        sa.Column(
            "admin_account_owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Create admin_account_patterns table (similar to service_account_patterns)
    op.create_table(
        "admin_account_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email_pattern", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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

    # Create index on email_pattern for faster lookups
    op.create_index(
        "ix_admin_account_patterns_email_pattern",
        "admin_account_patterns",
        ["email_pattern"],
    )

    # Create index on admin_account_owner_id for faster lookups
    op.create_index(
        "ix_licenses_admin_account_owner_id",
        "licenses",
        ["admin_account_owner_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_licenses_admin_account_owner_id", table_name="licenses")
    op.drop_index("ix_admin_account_patterns_email_pattern", table_name="admin_account_patterns")
    op.drop_table("admin_account_patterns")
    op.drop_column("licenses", "admin_account_owner_id")
    op.drop_column("licenses", "admin_account_name")
    op.drop_column("licenses", "is_admin_account")
