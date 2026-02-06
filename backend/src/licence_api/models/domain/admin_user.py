"""Admin user domain model."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr


class AuthProvider(StrEnum):
    """Authentication provider types."""

    LOCAL = "local"
    GOOGLE = "google"


class AdminUser(BaseModel):
    """Admin user domain model."""

    id: UUID
    email: EmailStr
    name: str | None = None
    picture_url: str | None = None
    auth_provider: AuthProvider = AuthProvider.LOCAL
    is_active: bool = True
    is_locked: bool = False
    require_password_change: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # RBAC
    roles: list[str] = []  # List of role codes
    permissions: list[str] = []  # Aggregated permission codes

    class Config:
        """Pydantic config."""

        from_attributes = True

    def has_permission(self, permission_code: str) -> bool:
        """Check if user has a specific permission.

        Super admins automatically have all permissions.

        Args:
            permission_code: Permission code to check

        Returns:
            True if user has the permission
        """
        # Super admins have all permissions
        if self.is_superadmin():
            return True
        return permission_code in self.permissions

    def has_any_permission(self, *permission_codes: str) -> bool:
        """Check if user has any of the specified permissions.

        Super admins automatically have all permissions.

        Args:
            permission_codes: Permission codes to check

        Returns:
            True if user has any of the permissions
        """
        # Super admins have all permissions
        if self.is_superadmin():
            return True
        return any(p in self.permissions for p in permission_codes)

    def has_all_permissions(self, *permission_codes: str) -> bool:
        """Check if user has all specified permissions.

        Super admins automatically have all permissions.

        Args:
            permission_codes: Permission codes to check

        Returns:
            True if user has all permissions
        """
        # Super admins have all permissions
        if self.is_superadmin():
            return True
        return all(p in self.permissions for p in permission_codes)

    def has_role(self, role_code: str) -> bool:
        """Check if user has a specific role.

        Args:
            role_code: Role code to check

        Returns:
            True if user has the role
        """
        return role_code in self.roles

    def is_superadmin(self) -> bool:
        """Check if user is a superadmin."""
        return "superadmin" in self.roles

    def is_admin(self) -> bool:
        """Check if user is an admin or higher."""
        return "superadmin" in self.roles or "admin" in self.roles


class AdminUserWithRoles(AdminUser):
    """Admin user with full role details."""

    role_details: list["Role"] = []


from licence_api.models.domain.role import Role

AdminUserWithRoles.model_rebuild()
