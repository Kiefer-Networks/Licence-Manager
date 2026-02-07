"""Add backup permissions.

Revision ID: 029
Revises: 028
Create Date: 2026-02-06 12:00:00.000000

"""

from datetime import UTC, datetime
from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "029"
down_revision: str = "028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add backup permissions."""
    conn = op.get_bind()

    # Backup permissions
    backup_permissions = [
        {
            "id": str(uuid4()),
            "code": "backups.view",
            "name": "View Backups",
            "description": "View backup list and configuration",
            "category": "backups",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "id": str(uuid4()),
            "code": "backups.create",
            "name": "Create Backups",
            "description": "Create manual backups",
            "category": "backups",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "id": str(uuid4()),
            "code": "backups.delete",
            "name": "Delete Backups",
            "description": "Delete stored backups",
            "category": "backups",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "id": str(uuid4()),
            "code": "backups.restore",
            "name": "Restore Backups",
            "description": "Restore system from backup",
            "category": "backups",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "id": str(uuid4()),
            "code": "backups.configure",
            "name": "Configure Backups",
            "description": "Change backup schedule and settings",
            "category": "backups",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    ]

    # Insert permissions
    for perm in backup_permissions:
        conn.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, name, description, category, created_at, updated_at)
                VALUES (:id, :code, :name, :description, :category, :created_at, :updated_at)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            perm,
        )

    # Note: System role permissions are now synced automatically by PermissionSyncService
    # on application startup, so we don't need to manually assign permissions here.


def downgrade() -> None:
    """Remove backup permissions."""
    conn = op.get_bind()

    # Remove role-permission assignments for backup permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE code LIKE 'backups.%'
            )
            """
        )
    )

    # Remove backup permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM permissions WHERE code LIKE 'backups.%'
            """
        )
    )
