"""Add TOTP two-factor authentication fields.

Revision ID: 023
Revises: 022
Create Date: 2026-02-04

This migration adds TOTP (Time-based One-Time Password) support:
- totp_secret_encrypted: Encrypted TOTP secret key
- totp_enabled: Whether 2FA is enabled for the user
- totp_verified_at: When TOTP was initially verified
- totp_backup_codes_encrypted: Encrypted backup codes for recovery
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add TOTP fields to admin_users table."""
    # Add TOTP columns to admin_users
    op.add_column(
        "admin_users",
        sa.Column("totp_secret_encrypted", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "admin_users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "admin_users",
        sa.Column("totp_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "admin_users",
        sa.Column("totp_backup_codes_encrypted", sa.LargeBinary(), nullable=True),
    )

    # Create index for efficient lookup of 2FA-enabled users
    op.create_index(
        "ix_admin_users_totp_enabled",
        "admin_users",
        ["totp_enabled"],
        unique=False,
    )


def downgrade() -> None:
    """Remove TOTP fields from admin_users table."""
    op.drop_index("ix_admin_users_totp_enabled", table_name="admin_users")
    op.drop_column("admin_users", "totp_backup_codes_encrypted")
    op.drop_column("admin_users", "totp_verified_at")
    op.drop_column("admin_users", "totp_enabled")
    op.drop_column("admin_users", "totp_secret_encrypted")
