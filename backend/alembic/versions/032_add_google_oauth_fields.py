"""Add Google OAuth fields to admin_users.

Revision ID: 032
Revises: 031
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add google_id field for Google OAuth authentication."""
    op.add_column(
        "admin_users",
        sa.Column("google_id", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_admin_users_google_id",
        "admin_users",
        ["google_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove google_id field."""
    op.drop_index("ix_admin_users_google_id", table_name="admin_users")
    op.drop_column("admin_users", "google_id")
