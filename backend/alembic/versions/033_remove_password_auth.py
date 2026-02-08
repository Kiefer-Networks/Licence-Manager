"""Remove password-based authentication fields.

Revision ID: 033
Revises: 032
Create Date: 2026-02-08

This migration removes all password and TOTP-related fields from admin_users
as part of the switch to Google-only OAuth authentication.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove password and TOTP fields from admin_users."""
    # Drop password_history table first (foreign key to admin_users)
    op.drop_table("password_history")

    # Remove password-related columns
    op.drop_column("admin_users", "password_hash")
    op.drop_column("admin_users", "password_changed_at")
    op.drop_column("admin_users", "require_password_change")

    # Remove security/lockout columns (not needed without passwords)
    op.drop_column("admin_users", "is_locked")
    op.drop_column("admin_users", "failed_login_attempts")
    op.drop_column("admin_users", "locked_until")

    # Remove TOTP columns
    op.drop_index("ix_admin_users_totp_enabled", table_name="admin_users")
    op.drop_column("admin_users", "totp_secret_encrypted")
    op.drop_column("admin_users", "totp_enabled")
    op.drop_column("admin_users", "totp_verified_at")
    op.drop_column("admin_users", "totp_backup_codes_encrypted")

    # Update auth_provider default to 'google'
    op.alter_column(
        "admin_users",
        "auth_provider",
        server_default="google",
    )


def downgrade() -> None:
    """Restore password and TOTP fields - NOT RECOMMENDED."""
    # Restore auth_provider default
    op.alter_column(
        "admin_users",
        "auth_provider",
        server_default="local",
    )

    # Restore TOTP columns
    op.add_column(
        "admin_users",
        sa.Column("totp_backup_codes_encrypted", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "admin_users",
        sa.Column("totp_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "admin_users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "admin_users",
        sa.Column("totp_secret_encrypted", sa.LargeBinary(), nullable=True),
    )
    op.create_index("ix_admin_users_totp_enabled", "admin_users", ["totp_enabled"])

    # Restore security columns
    op.add_column(
        "admin_users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "admin_users",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "admin_users",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Restore password columns
    op.add_column(
        "admin_users",
        sa.Column("require_password_change", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "admin_users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "admin_users",
        sa.Column("password_hash", sa.String(255), nullable=True),
    )

    # Recreate password_history table
    op.create_table(
        "password_history",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_password_history_user_id", "password_history", ["user_id"])
