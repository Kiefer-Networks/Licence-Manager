"""Add settings.delete permission.

Revision ID: 022
Revises: 021
Create Date: 2026-02-03

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add settings.delete permission
    op.execute(
        """
        INSERT INTO permissions (id, code, name, description, category)
        VALUES (gen_random_uuid(), 'settings.delete', 'Delete Settings', 'Delete system settings and notification rules', 'settings')
        ON CONFLICT (code) DO NOTHING
        """
    )

    # Assign to superadmin role
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.code = 'superadmin'
          AND p.code = 'settings.delete'
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
        """
    )

    # Assign to admin role (admins should be able to delete settings)
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.code = 'admin'
          AND p.code = 'settings.delete'
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
        """
    )


def downgrade() -> None:
    # Remove permission from role_permissions
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE code = 'settings.delete'
        )
        """
    )

    # Remove the permission
    op.execute(
        """
        DELETE FROM permissions
        WHERE code = 'settings.delete'
        """
    )
