"""Increase license_type column size for multiple license types.

Revision ID: 007_increase_license_type
Revises: 006_add_performance_indexes
Create Date: 2026-01-30

Microsoft 365 users can have multiple assigned licenses (e.g., E5, Power BI,
Teams, etc.) which are stored as comma-separated values. The previous limit
of 100 characters was insufficient for users with many licenses.

This migration increases the column size to 500 characters to accommodate
realistic license type combinations.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Increase license_type column from VARCHAR(100) to VARCHAR(500)."""
    op.alter_column(
        "licenses",
        "license_type",
        existing_type=sa.String(100),
        type_=sa.String(500),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert license_type column to VARCHAR(100).

    Note: This may truncate existing data that exceeds 100 characters.
    """
    op.alter_column(
        "licenses",
        "license_type",
        existing_type=sa.String(500),
        type_=sa.String(100),
        existing_nullable=True,
    )
