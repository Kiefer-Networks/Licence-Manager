"""Add locale preferences to admin_users.

Revision ID: 021
Revises: 020
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add locale preference columns to admin_users."""
    op.add_column(
        "admin_users",
        sa.Column("date_format", sa.String(20), nullable=True, default="DD.MM.YYYY"),
    )
    op.add_column(
        "admin_users",
        sa.Column("number_format", sa.String(20), nullable=True, default="de-DE"),
    )
    op.add_column(
        "admin_users",
        sa.Column("currency", sa.String(10), nullable=True, default="EUR"),
    )


def downgrade() -> None:
    """Remove locale preference columns from admin_users."""
    op.drop_column("admin_users", "currency")
    op.drop_column("admin_users", "number_format")
    op.drop_column("admin_users", "date_format")
