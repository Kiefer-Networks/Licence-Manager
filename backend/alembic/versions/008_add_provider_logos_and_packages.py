"""Add provider logos and license packages

Revision ID: 008
Revises: 007
Create Date: 2026-01-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add logo_url to providers
    op.add_column("providers", sa.Column("logo_url", sa.Text(), nullable=True))

    # Create license_packages table for tracking purchased seat counts
    op.create_table(
        "license_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("license_type", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("total_seats", sa.Integer(), nullable=False),
        sa.Column("cost_per_seat", sa.Numeric(10, 2), nullable=True),
        sa.Column("billing_cycle", sa.String(20), nullable=True),
        sa.Column("payment_frequency", sa.String(20), nullable=True),
        sa.Column("currency", sa.String(3), default="EUR", nullable=False),
        sa.Column("contract_start", sa.Date(), nullable=True),
        sa.Column("contract_end", sa.Date(), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), default=True, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("provider_id", "license_type", name="uq_package_provider_type"),
    )
    op.create_index("idx_license_packages_provider", "license_packages", ["provider_id"])

    # Add service account fields to licenses
    op.add_column("licenses", sa.Column("is_service_account", sa.Boolean(), default=False, nullable=False, server_default="false"))
    op.add_column("licenses", sa.Column("service_account_name", sa.String(255), nullable=True))
    op.add_column("licenses", sa.Column("service_account_owner_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_license_service_account_owner",
        "licenses",
        "employees",
        ["service_account_owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_licenses_service_account", "licenses", ["is_service_account"])

    # Create organization_licenses table
    op.create_table(
        "organization_licenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("license_type", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("monthly_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(3), default="EUR", nullable=False),
        sa.Column("billing_cycle", sa.String(20), nullable=True),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_org_licenses_provider", "organization_licenses", ["provider_id"])


def downgrade() -> None:
    # Drop organization_licenses
    op.drop_index("idx_org_licenses_provider", table_name="organization_licenses")
    op.drop_table("organization_licenses")

    # Remove service account fields from licenses
    op.drop_index("idx_licenses_service_account", table_name="licenses")
    op.drop_constraint("fk_license_service_account_owner", "licenses", type_="foreignkey")
    op.drop_column("licenses", "service_account_owner_id")
    op.drop_column("licenses", "service_account_name")
    op.drop_column("licenses", "is_service_account")

    # Drop license_packages
    op.drop_index("idx_license_packages_provider", table_name="license_packages")
    op.drop_table("license_packages")

    # Remove logo_url from providers
    op.drop_column("providers", "logo_url")
