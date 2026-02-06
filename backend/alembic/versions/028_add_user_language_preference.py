"""Add user language preference for email localization.

Revision ID: 028
Revises: 027
Create Date: 2026-02-06

This migration adds a language column to admin_users for email localization.
Supported values: 'en' (English), 'de' (German)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add language column to admin_users."""
    op.add_column(
        "admin_users",
        sa.Column("language", sa.String(5), nullable=False, server_default="en"),
    )


def downgrade() -> None:
    """Remove language column from admin_users."""
    op.drop_column("admin_users", "language")
