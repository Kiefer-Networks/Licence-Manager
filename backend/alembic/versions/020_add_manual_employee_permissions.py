"""Add manual employee management permissions.

Revision ID: 020
Revises: 019
Create Date: 2026-02-01

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new employee permissions
    permissions = [
        ("employees.create", "Create Employees", "Create manual employees", "employees"),
        ("employees.delete", "Delete Employees", "Delete manual employees", "employees"),
    ]

    for code, name, description, category in permissions:
        op.execute(
            f"""
            INSERT INTO permissions (id, code, name, description, category)
            VALUES (gen_random_uuid(), '{code}', '{name}', '{description}', '{category}')
            ON CONFLICT (code) DO NOTHING
            """
        )

    # Assign new permissions to superadmin role
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.code = 'superadmin'
          AND p.code IN ('employees.create', 'employees.delete')
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
        """
    )

    # Assign new permissions to admin role
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.code = 'admin'
          AND p.code IN ('employees.create', 'employees.delete')
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
        """
    )


def downgrade() -> None:
    # Remove permissions from role_permissions
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE code IN ('employees.create', 'employees.delete')
        )
        """
    )

    # Remove the permissions
    op.execute(
        """
        DELETE FROM permissions
        WHERE code IN ('employees.create', 'employees.delete')
        """
    )
