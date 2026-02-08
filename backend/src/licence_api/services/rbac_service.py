"""RBAC service for user, role, and permission management."""

import logging
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.exceptions import (
    CannotDeleteSelfError,
    CannotModifySystemRoleError,
    RoleAlreadyExistsError,
    RoleHasUsersError,
    RoleNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.auth import (
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    UserCreateRequest,
    UserCreateResponse,
    UserInfo,
    UserUpdateRequest,
)
from licence_api.repositories.audit_repository import AuditRepository
from licence_api.repositories.permission_repository import PermissionRepository
from licence_api.repositories.role_repository import RoleRepository
from licence_api.repositories.user_repository import RefreshTokenRepository, UserRepository

logger = logging.getLogger(__name__)


class RbacService:
    """Service for RBAC operations - Google OAuth only."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.permission_repo = PermissionRepository(session)
        self.token_repo = RefreshTokenRepository(session)
        self.audit_repo = AuditRepository(session)

    def _build_user_info(self, user) -> UserInfo:
        """Build UserInfo from user ORM object."""
        roles = [r.code for r in user.roles]
        permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.code)

        return UserInfo(
            id=user.id,
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
            auth_provider=user.auth_provider,
            is_active=user.is_active,
            roles=roles,
            permissions=sorted(permissions),
            is_superadmin="superadmin" in roles,
            last_login_at=user.last_login_at,
            language=getattr(user, "language", "en") or "en",
            date_format=user.date_format,
            number_format=user.number_format,
            currency=user.currency,
        )

    async def list_users(self) -> list[UserInfo]:
        """List all users with their roles."""
        users = await self.user_repo.get_all_with_roles()
        return [self._build_user_info(user) for user in users]

    async def create_user(
        self,
        request: UserCreateRequest,
        current_user: AdminUser,
        http_request: Request | None = None,
        user_agent: str | None = None,
    ) -> UserCreateResponse:
        """Create a new user for Google OAuth authentication.

        Users are created with email and roles only - no password needed.
        They authenticate via Google when they first log in.

        Args:
            request: User creation request
            current_user: Admin user creating the new user
            http_request: HTTP request for audit logging
            user_agent: User agent string

        Returns:
            UserCreateResponse with user info

        Raises:
            UserAlreadyExistsError: If email exists
        """
        # Check if email already exists
        existing = await self.user_repo.get_by_email(request.email.lower())
        if existing:
            raise UserAlreadyExistsError(request.email)

        # Create user without password (Google OAuth only)
        user = await self.user_repo.create_user(
            email=request.email.lower(),
            password_hash=None,
            name=request.name,
            auth_provider="google",
            require_password_change=False,
            language=request.language,
        )

        # Assign roles
        if request.role_codes:
            roles = await self.role_repo.get_by_codes(request.role_codes)
            role_ids = [r.id for r in roles]
            await self.user_repo.set_roles(user.id, role_ids, assigned_by=current_user.id)

        # Audit log
        ip_address = http_request.client.host if http_request and http_request.client else None
        await self.audit_repo.log(
            action="create",
            resource_type="admin_user",
            resource_id=user.id,
            admin_user_id=current_user.id,
            changes={
                "email": user.email,
                "name": user.name,
                "roles": request.role_codes or [],
                "auth_provider": "google",
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

        # Fetch user with roles
        user = await self.user_repo.get_with_roles(user.id)
        user_info = self._build_user_info(user)

        return UserCreateResponse(user=user_info)

    async def get_user(self, user_id: UUID) -> UserInfo | None:
        """Get user by ID."""
        user = await self.user_repo.get_with_roles(user_id)
        if user is None:
            return None
        return self._build_user_info(user)

    async def update_user(
        self,
        user_id: UUID,
        request: UserUpdateRequest,
        current_user: AdminUser,
    ) -> UserInfo:
        """Update user details."""
        user = await self.user_repo.get_with_roles(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        # Prevent deactivating yourself
        if request.is_active is False and user_id == current_user.id:
            raise ValidationError("Cannot deactivate your own account")

        # Update fields
        if request.email is not None and request.email != user.email:
            existing = await self.user_repo.get_by_email(request.email)
            if existing is not None:
                raise UserAlreadyExistsError(request.email)
            user.email = request.email

        if request.name is not None:
            user.name = request.name

        if request.is_active is not None:
            user.is_active = request.is_active

        # Update roles if provided
        if request.role_codes is not None:
            if user_id == current_user.id and "superadmin" in current_user.roles:
                if "superadmin" not in request.role_codes:
                    raise ValidationError("Cannot remove superadmin role from yourself")

            roles = await self.role_repo.get_by_codes(request.role_codes)
            role_ids = [r.id for r in roles]
            await self.user_repo.set_roles(user_id, role_ids, assigned_by=current_user.id)

        await self.session.commit()

        user = await self.user_repo.get_with_roles(user_id)
        return self._build_user_info(user)

    async def delete_user(
        self,
        user_id: UUID,
        current_user: AdminUser,
        http_request: Request | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Delete a user."""
        if user_id == current_user.id:
            raise CannotDeleteSelfError()

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        ip_address = http_request.client.host if http_request and http_request.client else None
        await self.audit_repo.log(
            action="delete",
            resource_type="admin_user",
            resource_id=user_id,
            admin_user_id=current_user.id,
            changes={"email": user.email},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.user_repo.delete_user(user_id)
        await self.session.commit()

    # =========================================================================
    # Role Management
    # =========================================================================

    async def list_roles(self) -> list[RoleResponse]:
        """List all roles with their permissions."""
        roles = await self.role_repo.get_all_with_permissions()
        return [
            RoleResponse(
                id=r.id,
                code=r.code,
                name=r.name,
                description=r.description,
                is_system=r.is_system,
                priority=r.priority,
                permissions=[p.code for p in r.permissions],
            )
            for r in roles
        ]

    async def create_role(self, request: RoleCreateRequest) -> RoleResponse:
        """Create a custom role."""
        existing = await self.role_repo.get_by_code(request.code)
        if existing:
            raise RoleAlreadyExistsError(request.code)

        role = await self.role_repo.create_role(
            code=request.code,
            name=request.name,
            description=request.description,
            is_system=False,
            priority=50,
        )

        if request.permission_codes:
            permissions = await self.permission_repo.get_by_codes(request.permission_codes)
            permission_ids = [p.id for p in permissions]
            await self.role_repo.set_permissions(role.id, permission_ids)

        await self.session.commit()

        role = await self.role_repo.get_with_permissions(role.id)

        return RoleResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            priority=role.priority,
            permissions=[p.code for p in role.permissions],
        )

    async def get_role(self, role_id: UUID) -> RoleResponse | None:
        """Get role by ID."""
        role = await self.role_repo.get_with_permissions(role_id)
        if role is None:
            return None

        return RoleResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            priority=role.priority,
            permissions=[p.code for p in role.permissions],
        )

    async def update_role(
        self,
        role_id: UUID,
        request: RoleUpdateRequest,
        current_user: AdminUser,
    ) -> RoleResponse:
        """Update a role."""
        role = await self.role_repo.get_with_permissions(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id))

        if role.is_system and not current_user.is_superadmin():
            raise CannotModifySystemRoleError(role.code)

        if request.name is not None:
            role.name = request.name

        if request.description is not None:
            role.description = request.description

        if request.permission_codes is not None:
            permissions = await self.permission_repo.get_by_codes(request.permission_codes)
            permission_ids = [p.id for p in permissions]
            await self.role_repo.set_permissions(role_id, permission_ids)

        await self.session.commit()

        role = await self.role_repo.get_with_permissions(role_id)

        return RoleResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            priority=role.priority,
            permissions=[p.code for p in role.permissions],
        )

    async def delete_role(self, role_id: UUID) -> None:
        """Delete a custom role."""
        role = await self.role_repo.get_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id))

        if role.is_system:
            raise CannotModifySystemRoleError(role.code)

        user_count = await self.role_repo.count_users_with_role(role_id)
        if user_count > 0:
            raise RoleHasUsersError(role.code, user_count)

        await self.role_repo.delete_role(role_id)
        await self.session.commit()

    # =========================================================================
    # Permission Management
    # =========================================================================

    async def list_permissions(self) -> list:
        """List all permissions."""
        return await self.permission_repo.get_all()

    async def get_permission_categories(self) -> list[str]:
        """Get all permission categories."""
        return await self.permission_repo.get_categories()

    async def get_permissions_by_category(self, category: str) -> list:
        """Get permissions for a specific category."""
        return await self.permission_repo.get_by_category(category)

    # =========================================================================
    # Session Management
    # =========================================================================

    async def get_user_sessions(self, user_id: UUID) -> list:
        """Get active sessions for a user."""
        return await self.token_repo.get_active_sessions(user_id)
