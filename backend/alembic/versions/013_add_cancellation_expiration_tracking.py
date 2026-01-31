"""Add cancellation and expiration tracking.

Revision ID: 013
Revises: 012
Create Date: 2026-01-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to licenses table
    op.add_column(
        "licenses",
        sa.Column("expires_at", sa.Date(), nullable=True),
    )
    op.add_column(
        "licenses",
        sa.Column("needs_reorder", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "licenses",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "licenses",
        sa.Column("cancellation_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "licenses",
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "licenses",
        sa.Column(
            "cancelled_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Add new columns to license_packages table
    op.add_column(
        "license_packages",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "license_packages",
        sa.Column("cancellation_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "license_packages",
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "license_packages",
        sa.Column(
            "cancelled_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "license_packages",
        sa.Column("needs_reorder", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "license_packages",
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
    )

    # Add new columns to organization_licenses table
    op.add_column(
        "organization_licenses",
        sa.Column("expires_at", sa.Date(), nullable=True),
    )
    op.add_column(
        "organization_licenses",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_licenses",
        sa.Column("cancellation_effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "organization_licenses",
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "organization_licenses",
        sa.Column(
            "cancelled_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "organization_licenses",
        sa.Column("needs_reorder", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "organization_licenses",
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
    )

    # Create indexes for better query performance
    op.create_index("idx_licenses_expires_at", "licenses", ["expires_at"])
    op.create_index("idx_licenses_cancelled_at", "licenses", ["cancelled_at"])
    op.create_index("idx_licenses_needs_reorder", "licenses", ["needs_reorder"])

    op.create_index("idx_license_packages_cancelled_at", "license_packages", ["cancelled_at"])
    op.create_index("idx_license_packages_status", "license_packages", ["status"])
    op.create_index("idx_license_packages_needs_reorder", "license_packages", ["needs_reorder"])

    op.create_index("idx_org_licenses_expires_at", "organization_licenses", ["expires_at"])
    op.create_index("idx_org_licenses_cancelled_at", "organization_licenses", ["cancelled_at"])
    op.create_index("idx_org_licenses_status", "organization_licenses", ["status"])
    op.create_index("idx_org_licenses_needs_reorder", "organization_licenses", ["needs_reorder"])

    # Migrate valid_until from metadata to expires_at for manual licenses
    op.execute("""
        UPDATE licenses
        SET expires_at = (metadata->>'valid_until')::date
        WHERE metadata->>'valid_until' IS NOT NULL
        AND metadata->>'valid_until' != ''
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_org_licenses_needs_reorder", table_name="organization_licenses")
    op.drop_index("idx_org_licenses_status", table_name="organization_licenses")
    op.drop_index("idx_org_licenses_cancelled_at", table_name="organization_licenses")
    op.drop_index("idx_org_licenses_expires_at", table_name="organization_licenses")

    op.drop_index("idx_license_packages_needs_reorder", table_name="license_packages")
    op.drop_index("idx_license_packages_status", table_name="license_packages")
    op.drop_index("idx_license_packages_cancelled_at", table_name="license_packages")

    op.drop_index("idx_licenses_needs_reorder", table_name="licenses")
    op.drop_index("idx_licenses_cancelled_at", table_name="licenses")
    op.drop_index("idx_licenses_expires_at", table_name="licenses")

    # Drop columns from organization_licenses
    op.drop_column("organization_licenses", "status")
    op.drop_column("organization_licenses", "needs_reorder")
    op.drop_column("organization_licenses", "cancelled_by")
    op.drop_column("organization_licenses", "cancellation_reason")
    op.drop_column("organization_licenses", "cancellation_effective_date")
    op.drop_column("organization_licenses", "cancelled_at")
    op.drop_column("organization_licenses", "expires_at")

    # Drop columns from license_packages
    op.drop_column("license_packages", "status")
    op.drop_column("license_packages", "needs_reorder")
    op.drop_column("license_packages", "cancelled_by")
    op.drop_column("license_packages", "cancellation_reason")
    op.drop_column("license_packages", "cancellation_effective_date")
    op.drop_column("license_packages", "cancelled_at")

    # Drop columns from licenses
    op.drop_column("licenses", "cancelled_by")
    op.drop_column("licenses", "cancellation_reason")
    op.drop_column("licenses", "cancellation_effective_date")
    op.drop_column("licenses", "cancelled_at")
    op.drop_column("licenses", "needs_reorder")
    op.drop_column("licenses", "expires_at")
