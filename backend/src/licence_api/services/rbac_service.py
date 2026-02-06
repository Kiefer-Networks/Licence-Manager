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
    PasswordResetResponse,
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
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.security.password import get_password_service
from licence_api.services.email_service import EmailService

logger = logging.getLogger(__name__)


class RbacService:
    """Service for RBAC operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.permission_repo = PermissionRepository(session)
        self.token_repo = RefreshTokenRepository(session)
        self.audit_repo = AuditRepository(session)
        self.settings_repo = SettingsRepository(session)
        self.password_service = get_password_service()
        self.email_service = EmailService(session)

    async def _get_password_policy(self):
        """Get password policy from settings.

        Returns:
            PasswordPolicySettings from database or defaults
        """
        from licence_api.models.dto.password_policy import PasswordPolicySettings

        policy_data = await self.settings_repo.get("password_policy")
        if policy_data is None:
            return PasswordPolicySettings()
        return PasswordPolicySettings(**policy_data)

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
            require_password_change=user.require_password_change,
            roles=roles,
            permissions=sorted(permissions),
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
        """Create a new user with local authentication.

        If email is configured, password can be auto-generated and sent via email.
        If email is not configured, password must be provided in the request.

        Args:
            request: User creation request
            current_user: Admin user creating the new user
            http_request: HTTP request for audit logging
            user_agent: User agent string

        Returns:
            UserCreateResponse with user info and password delivery status

        Raises:
            UserAlreadyExistsError: If email exists
            ValidationError: If password invalid or required but not provided
        """
        # Check if email already exists
        existing = await self.user_repo.get_by_email(request.email.lower())
        if existing:
            raise UserAlreadyExistsError(request.email)

        # Get password policy from settings
        password_policy = await self._get_password_policy()

        # Check if email is configured
        email_configured = await self.email_service.is_configured()

        # Determine password
        password: str
        password_sent_via_email = False
        temporary_password: str | None = None

        if request.password:
            # Use provided password - validate against policy
            password = request.password
            is_valid, errors = self.password_service.validate_password_strength(
                password, policy=password_policy
            )
            if not is_valid:
                raise ValidationError(errors[0])
        elif email_configured:
            # Auto-generate password for email delivery using policy
            password = self.password_service.generate_temporary_password(
                policy=password_policy
            )
        else:
            # No email and no password provided
            raise ValidationError("Password is required when email is not configured")

        # Hash password
        password_hash = self.password_service.hash_password(password)

        # Create user with language preference
        user = await self.user_repo.create_user(
            email=request.email.lower(),
            password_hash=password_hash,
            name=request.name,
            auth_provider="local",
            require_password_change=True,
            language=request.language,
        )

        # Assign roles
        if request.role_codes:
            roles = await self.role_repo.get_by_codes(request.role_codes)
            role_ids = [r.id for r in roles]
            await self.user_repo.set_roles(user.id, role_ids, assigned_by=current_user.id)

        # Send password via email if configured and password was auto-generated
        if email_configured and not request.password:
            email_sent = await self.email_service.send_password_email(
                to_email=request.email.lower(),
                user_name=request.name,
                password=password,
                is_new_user=True,
                language=request.language,
            )
            if email_sent:
                password_sent_via_email = True
            else:
                # Email failed but user was created - log warning and return password
                logger.warning(f"Failed to send password email to {request.email}, returning password in response")
                temporary_password = password
        elif not request.password:
            # No email configured, return password in response
            temporary_password = password

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
                "password_sent_via_email": password_sent_via_email,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

        # Fetch user with roles
        user = await self.user_repo.get_with_roles(user.id)
        user_info = self._build_user_info(user)

        return UserCreateResponse(
            user=user_info,
            password_sent_via_email=password_sent_via_email,
            temporary_password=temporary_password,
        )

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
        """Update user details.

        Args:
            user_id: User ID to update
            request: Update request
            current_user: Admin user making the update

        Returns:
            Updated user info

        Raises:
            UserNotFoundError: If user not found
            ValidationError: If validation fails
        """
        user = await self.user_repo.get_with_roles(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        # Prevent deactivating yourself
        if request.is_active is False and user_id == current_user.id:
            raise ValidationError("Cannot deactivate your own account")

        # Update fields
        if request.email is not None and request.email != user.email:
            # Check if email is already taken
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
            # Prevent removing superadmin role from yourself
            if user_id == current_user.id and "superadmin" in current_user.roles:
                if "superadmin" not in request.role_codes:
                    raise ValidationError("Cannot remove superadmin role from yourself")

            roles = await self.role_repo.get_by_codes(request.role_codes)
            role_ids = [r.id for r in roles]
            await self.user_repo.set_roles(user_id, role_ids, assigned_by=current_user.id)

        await self.session.commit()

        # Fetch updated user
        user = await self.user_repo.get_with_roles(user_id)
        return self._build_user_info(user)

    async def delete_user(
        self,
        user_id: UUID,
        current_user: AdminUser,
        http_request: Request | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Delete a user.

        Args:
            user_id: User ID to delete
            current_user: Admin user making the deletion
            http_request: HTTP request for audit logging
            user_agent: User agent string

        Raises:
            CannotDeleteSelfError: If trying to delete self
            UserNotFoundError: If user not found
        """
        # Prevent deleting yourself
        if user_id == current_user.id:
            raise CannotDeleteSelfError()

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        # Audit log before deletion
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

        # Delete user
        await self.user_repo.delete_user(user_id)
        await self.session.commit()

    async def reset_user_password(
        self,
        user_id: UUID,
        current_user: AdminUser,
        http_request: Request | None = None,
        user_agent: str | None = None,
    ) -> PasswordResetResponse:
        """Reset a user's password.

        Generates a new temporary password. If email is configured,
        sends the password via email. Otherwise, returns the password
        in the response.

        Args:
            user_id: User ID to reset password for
            current_user: Admin user performing reset
            http_request: HTTP request for audit logging
            user_agent: User agent string

        Returns:
            PasswordResetResponse with password delivery status

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        # Get password policy from settings
        password_policy = await self._get_password_policy()

        # Generate new temporary password using policy
        new_password = self.password_service.generate_temporary_password(
            policy=password_policy
        )

        # Hash and update password
        password_hash = self.password_service.hash_password(new_password)
        await self.user_repo.update_password(
            user_id,
            password_hash,
            require_change=True,
        )

        # Revoke all sessions
        await self.token_repo.revoke_all_for_user(user_id)

        # Check if email is configured and try to send password
        email_configured = await self.email_service.is_configured()
        password_sent_via_email = False
        temporary_password: str | None = None

        if email_configured:
            # Use the user's preferred language for the email
            user_language = getattr(user, "language", "en") or "en"
            email_sent = await self.email_service.send_password_email(
                to_email=user.email,
                user_name=user.name,
                password=new_password,
                is_new_user=False,
                language=user_language,
            )
            if email_sent:
                password_sent_via_email = True
            else:
                # Email failed - log warning and return password
                logger.warning(
                    f"Failed to send password reset email to {user.email}, "
                    "returning password in response"
                )
                temporary_password = new_password
        else:
            # No email configured, return password in response
            temporary_password = new_password

        # Audit log
        ip_address = http_request.client.host if http_request and http_request.client else None
        await self.audit_repo.log(
            action="password_reset",
            resource_type="admin_user",
            resource_id=user_id,
            admin_user_id=current_user.id,
            changes={
                "target_email": user.email,
                "require_change": True,
                "password_sent_via_email": password_sent_via_email,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

        return PasswordResetResponse(
            message="Password reset successfully",
            password_sent_via_email=password_sent_via_email,
            temporary_password=temporary_password,
        )

    async def unlock_user(self, user_id: UUID) -> bool:
        """Unlock a locked user account.

        Args:
            user_id: User ID to unlock

        Returns:
            True if user was unlocked

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.unlock_user(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        await self.session.commit()
        return True

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
        """Create a custom role.

        Args:
            request: Role creation request

        Returns:
            Created role

        Raises:
            RoleAlreadyExistsError: If role code already exists
        """
        # Check if role code already exists
        existing = await self.role_repo.get_by_code(request.code)
        if existing:
            raise RoleAlreadyExistsError(request.code)

        # Create role
        role = await self.role_repo.create_role(
            code=request.code,
            name=request.name,
            description=request.description,
            is_system=False,
            priority=50,
        )

        # Set permissions
        if request.permission_codes:
            permissions = await self.permission_repo.get_by_codes(request.permission_codes)
            permission_ids = [p.id for p in permissions]
            await self.role_repo.set_permissions(role.id, permission_ids)

        await self.session.commit()

        # Fetch updated role
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
        """Update a role.

        Args:
            role_id: Role ID to update
            request: Update request
            current_user: Admin user making the update

        Returns:
            Updated role

        Raises:
            RoleNotFoundError: If role not found
            CannotModifySystemRoleError: If trying to modify system role without permission
        """
        role = await self.role_repo.get_with_permissions(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id))

        # System roles can only have permissions changed by superadmin
        if role.is_system and not current_user.is_superadmin():
            raise CannotModifySystemRoleError(role.code)

        # Update fields
        if request.name is not None:
            role.name = request.name

        if request.description is not None:
            role.description = request.description

        # Update permissions
        if request.permission_codes is not None:
            permissions = await self.permission_repo.get_by_codes(request.permission_codes)
            permission_ids = [p.id for p in permissions]
            await self.role_repo.set_permissions(role_id, permission_ids)

        await self.session.commit()

        # Fetch updated role
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
        """Delete a custom role.

        Args:
            role_id: Role ID to delete

        Raises:
            RoleNotFoundError: If role not found
            CannotModifySystemRoleError: If role is a system role
            RoleHasUsersError: If role has users assigned
        """
        role = await self.role_repo.get_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id))

        if role.is_system:
            raise CannotModifySystemRoleError(role.code)

        # Check if role has users assigned
        user_count = await self.role_repo.count_users_with_role(role_id)
        if user_count > 0:
            raise RoleHasUsersError(role.code, user_count)

        await self.role_repo.delete_role(role_id)
        await self.session.commit()

    # =========================================================================
    # Permission Management
    # =========================================================================

    async def list_permissions(self) -> list:
        """List all permissions.

        Returns:
            List of permission ORM objects
        """
        return await self.permission_repo.get_all()

    async def get_permission_categories(self) -> list[str]:
        """Get all permission categories.

        Returns:
            List of category names
        """
        return await self.permission_repo.get_categories()

    async def get_permissions_by_category(self, category: str) -> list:
        """Get permissions for a specific category.

        Args:
            category: Category name

        Returns:
            List of permission ORM objects
        """
        return await self.permission_repo.get_by_category(category)

    # =========================================================================
    # Session Management
    # =========================================================================

    async def get_user_sessions(self, user_id: UUID) -> list:
        """Get active sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of session ORM objects
        """
        return await self.token_repo.get_active_sessions(user_id)
