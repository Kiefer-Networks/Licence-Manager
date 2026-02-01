"""Add service account license types table.

Revision ID: 018
Revises: 017
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create service_account_license_types table
    op.create_table(
        "service_account_license_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("license_type", sa.String(500), nullable=False, unique=True),
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
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create index for license type lookups
    op.create_index(
        "ix_service_account_license_types_license_type",
        "service_account_license_types",
        ["license_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_service_account_license_types_license_type", table_name="service_account_license_types")
    op.drop_table("service_account_license_types")
