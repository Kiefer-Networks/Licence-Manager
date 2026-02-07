"""Add external_user_id indexes for performance.

Revision ID: 030
Revises: 029
Create Date: 2026-02-06

These indexes optimize queries that filter on external_user_id,
especially LIKE queries for detecting external email addresses.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes for external_user_id optimization."""
    # Index on external_user_id for faster email lookups
    op.create_index(
        "idx_licenses_external_user_id",
        "licenses",
        ["external_user_id"],
        if_not_exists=True,
    )

    # Composite index for queries filtering status AND external_user_id
    op.create_index(
        "idx_licenses_status_external",
        "licenses",
        ["status", "external_user_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    """Remove external_user_id indexes."""
    op.drop_index("idx_licenses_status_external", table_name="licenses", if_exists=True)
    op.drop_index("idx_licenses_external_user_id", table_name="licenses", if_exists=True)
