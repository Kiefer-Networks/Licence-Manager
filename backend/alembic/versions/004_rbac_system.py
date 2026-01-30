"""RBAC system with roles, permissions, and local auth.

Revision ID: 004
Revises: 003
Create Date: 2026-01-29

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create permissions table
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("code", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("code", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, default=False, nullable=False),
        sa.Column("priority", sa.Integer, default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create role_permissions junction table
    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create user_roles junction table
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
    )

    # Add new columns to admin_users for local auth
    op.add_column("admin_users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column("admin_users", sa.Column("is_active", sa.Boolean, default=True, nullable=False, server_default="true"))
    op.add_column("admin_users", sa.Column("is_locked", sa.Boolean, default=False, nullable=False, server_default="false"))
    op.add_column("admin_users", sa.Column("failed_login_attempts", sa.Integer, default=0, nullable=False, server_default="0"))
    op.add_column("admin_users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("admin_users", sa.Column("auth_provider", sa.String(50), default="local", nullable=False, server_default="local"))
    op.add_column("admin_users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("admin_users", sa.Column("require_password_change", sa.Boolean, default=False, nullable=False, server_default="false"))

    # Create refresh_tokens table for token management
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )

    # Create password_history table to prevent reuse
    op.create_table(
        "password_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Insert default permissions
    permissions = [
        # Dashboard
        ("dashboard.view", "View Dashboard", "Access to view dashboard", "dashboard"),
        
        # Users
        ("users.view", "View Users", "View user list and details", "users"),
        ("users.create", "Create Users", "Create new users", "users"),
        ("users.edit", "Edit Users", "Modify user information", "users"),
        ("users.delete", "Delete Users", "Delete users", "users"),
        ("users.manage_roles", "Manage User Roles", "Assign and remove user roles", "users"),
        
        # Roles
        ("roles.view", "View Roles", "View role list and details", "roles"),
        ("roles.create", "Create Roles", "Create custom roles", "roles"),
        ("roles.edit", "Edit Roles", "Modify role permissions", "roles"),
        ("roles.delete", "Delete Roles", "Delete custom roles", "roles"),
        
        # Providers
        ("providers.view", "View Providers", "View provider list and details", "providers"),
        ("providers.create", "Create Providers", "Add new providers", "providers"),
        ("providers.edit", "Edit Providers", "Modify provider settings", "providers"),
        ("providers.delete", "Delete Providers", "Remove providers", "providers"),
        ("providers.sync", "Sync Providers", "Trigger provider synchronization", "providers"),
        
        # Licenses
        ("licenses.view", "View Licenses", "View license list and details", "licenses"),
        ("licenses.create", "Create Licenses", "Create manual licenses", "licenses"),
        ("licenses.edit", "Edit Licenses", "Modify license information", "licenses"),
        ("licenses.delete", "Delete Licenses", "Delete licenses", "licenses"),
        ("licenses.assign", "Assign Licenses", "Assign licenses to employees", "licenses"),
        ("licenses.bulk_actions", "Bulk License Actions", "Perform bulk operations on licenses", "licenses"),
        
        # Employees
        ("employees.view", "View Employees", "View employee list and details", "employees"),
        ("employees.edit", "Edit Employees", "Modify employee information", "employees"),
        
        # Reports
        ("reports.view", "View Reports", "Access to view reports", "reports"),
        ("reports.export", "Export Reports", "Export report data", "reports"),
        
        # Settings
        ("settings.view", "View Settings", "View system settings", "settings"),
        ("settings.edit", "Edit Settings", "Modify system settings", "settings"),
        
        # Payment Methods
        ("payment_methods.view", "View Payment Methods", "View payment methods", "payment_methods"),
        ("payment_methods.create", "Create Payment Methods", "Add payment methods", "payment_methods"),
        ("payment_methods.edit", "Edit Payment Methods", "Modify payment methods", "payment_methods"),
        ("payment_methods.delete", "Delete Payment Methods", "Remove payment methods", "payment_methods"),
        
        # Audit
        ("audit.view", "View Audit Logs", "Access to audit logs", "audit"),
        ("audit.export", "Export Audit Logs", "Export audit log data", "audit"),
        
        # System
        ("system.admin", "System Administration", "Full system administration access", "system"),
    ]

    for code, name, description, category in permissions:
        op.execute(
            f"""
            INSERT INTO permissions (id, code, name, description, category)
            VALUES (gen_random_uuid(), '{code}', '{name}', '{description}', '{category}')
            """
        )

    # Insert default roles
    roles = [
        ("superadmin", "Super Administrator", "Full system access with all permissions", True, 100),
        ("admin", "Administrator", "Administrative access to manage users and settings", True, 80),
        ("auditor", "Auditor", "Read-only access for compliance and auditing", True, 60),
    ]

    for code, name, description, is_system, priority in roles:
        op.execute(
            f"""
            INSERT INTO roles (id, code, name, description, is_system, priority)
            VALUES (gen_random_uuid(), '{code}', '{name}', '{description}', {is_system}, {priority})
            """
        )

    # Assign all permissions to superadmin
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.code = 'superadmin'
        """
    )

    # Assign admin permissions (exclude system.admin and some sensitive ones)
    admin_permissions = [
        "dashboard.view", "users.view", "users.create", "users.edit", 
        "roles.view", "providers.view", "providers.create", "providers.edit", 
        "providers.delete", "providers.sync", "licenses.view", "licenses.create", 
        "licenses.edit", "licenses.delete", "licenses.assign", "licenses.bulk_actions",
        "employees.view", "employees.edit", "reports.view", "reports.export",
        "settings.view", "settings.edit", "payment_methods.view", 
        "payment_methods.create", "payment_methods.edit", "payment_methods.delete",
        "audit.view"
    ]
    
    for perm in admin_permissions:
        op.execute(
            f"""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.code = 'admin' AND p.code = '{perm}'
            """
        )

    # Assign auditor permissions (read-only)
    auditor_permissions = [
        "dashboard.view", "users.view", "roles.view", "providers.view", 
        "licenses.view", "employees.view", "reports.view", "reports.export",
        "settings.view", "payment_methods.view", "audit.view", "audit.export"
    ]
    
    for perm in auditor_permissions:
        op.execute(
            f"""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.code = 'auditor' AND p.code = '{perm}'
            """
        )

    # Migrate existing users - assign superadmin role to existing admins
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM admin_users u, roles r
        WHERE u.role = 'admin' AND r.code = 'superadmin'
        """
    )

    # Assign admin role to existing viewers
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM admin_users u, roles r
        WHERE u.role = 'viewer' AND r.code = 'auditor'
        """
    )

    # Drop old role column from admin_users (after migration)
    op.drop_column("admin_users", "role")

    # Create indexes for performance
    op.create_index("ix_refresh_tokens_user_expires", "refresh_tokens", ["user_id", "expires_at"])
    op.create_index("ix_password_history_user", "password_history", ["user_id", "created_at"])


def downgrade() -> None:
    # Add back role column
    op.add_column("admin_users", sa.Column("role", sa.String(50), default="viewer", nullable=False, server_default="viewer"))
    
    # Restore role from user_roles
    op.execute(
        """
        UPDATE admin_users u
        SET role = CASE 
            WHEN EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = u.id AND r.code = 'superadmin') THEN 'admin'
            WHEN EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = u.id AND r.code = 'admin') THEN 'admin'
            ELSE 'viewer'
        END
        """
    )
    
    # Drop indexes
    op.drop_index("ix_password_history_user")
    op.drop_index("ix_refresh_tokens_user_expires")
    
    # Drop tables
    op.drop_table("password_history")
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
    
    # Drop new columns from admin_users
    op.drop_column("admin_users", "require_password_change")
    op.drop_column("admin_users", "password_changed_at")
    op.drop_column("admin_users", "auth_provider")
    op.drop_column("admin_users", "locked_until")
    op.drop_column("admin_users", "failed_login_attempts")
    op.drop_column("admin_users", "is_locked")
    op.drop_column("admin_users", "is_active")
    op.drop_column("admin_users", "password_hash")
