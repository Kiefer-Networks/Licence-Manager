"""Authentication service."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.config import get_settings
from licence_api.models.dto.auth import TokenResponse, UserInfo
from licence_api.repositories.audit_repository import AuditRepository
from licence_api.repositories.role_repository import RoleRepository
from licence_api.repositories.user_repository import RefreshTokenRepository, UserRepository
from licence_api.security.auth import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_google_token,
)
from licence_api.security.password import get_password_service


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.token_repo = RefreshTokenRepository(session)
        self.audit_repo = AuditRepository(session)
        self.password_service = get_password_service()

    async def authenticate_local(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Authenticate with email and password.

        Args:
            email: User email
            password: User password
            user_agent: User agent string
            ip_address: IP address

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            HTTPException: If authentication fails
        """
        user = await self.user_repo.get_by_email(email.lower())

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        # Check if account is locked
        if user.is_locked:
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is locked. Try again later.",
                )
            else:
                # Lock expired, unlock the account
                await self.user_repo.unlock_user(user.id)

        # Check if user has a password (local auth)
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Verify password
        if not self.password_service.verify_password(password, user.password_hash):
            await self.user_repo.record_failed_login(user.id)
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Successful login
        await self.user_repo.record_successful_login(user.id)

        # Get user permissions
        roles, permissions = self._aggregate_permissions(user)

        # Create tokens
        settings = get_settings()
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            roles=roles,
            permissions=permissions,
        )

        raw_refresh, refresh_hash = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)

        await self.token_repo.create_token(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Audit log
        await self.audit_repo.log(
            action="login",
            resource_type="admin_user",
            resource_id=user.id,
            admin_user_id=user.id,
            changes={"method": "local", "email": user.email},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.jwt_expiration_hours * 3600,
        )

    async def authenticate_google(
        self,
        id_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Authenticate with Google OAuth.

        Args:
            id_token: Google ID token
            user_agent: User agent string
            ip_address: IP address

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            HTTPException: If authentication fails
        """
        # Verify Google token
        google_info = await verify_google_token(id_token)

        # Get or create user
        user = await self.user_repo.get_by_email(google_info.email.lower())

        if user is None:
            # Check if this is the first user (becomes superadmin)
            active_users = await self.user_repo.count_active_users()
            is_first_user = active_users == 0

            user = await self.user_repo.create_user(
                email=google_info.email.lower(),
                name=google_info.name,
                picture_url=google_info.picture,
                auth_provider="google",
            )

            # Assign appropriate role
            if is_first_user:
                role = await self.role_repo.get_by_code("superadmin")
            else:
                role = await self.role_repo.get_by_code("auditor")

            if role:
                await self.user_repo.add_role(user.id, role.id)

            # Refresh user to get roles
            user = await self.user_repo.get_with_roles(user.id)
        else:
            # Update user info from Google
            user.name = google_info.name
            user.picture_url = google_info.picture
            await self.session.flush()

            # Check if account is active
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is disabled",
                )

        # Record successful login
        await self.user_repo.record_successful_login(user.id)

        # Get user permissions
        roles, permissions = self._aggregate_permissions(user)

        # Create tokens
        settings = get_settings()
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            roles=roles,
            permissions=permissions,
        )

        raw_refresh, refresh_hash = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)

        await self.token_repo.create_token(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Audit log
        await self.audit_repo.log(
            action="login",
            resource_type="admin_user",
            resource_id=user.id,
            admin_user_id=user.id,
            changes={"method": "google", "email": user.email},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.jwt_expiration_hours * 3600,
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> TokenResponse:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New TokenResponse

        Raises:
            HTTPException: If refresh token is invalid
        """
        token_hash = hash_refresh_token(refresh_token)
        token_record = await self.token_repo.get_by_hash(token_hash)

        if token_record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if token_record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )

        # Get user with roles
        user = await self.user_repo.get_with_roles(token_record.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Get user permissions
        roles, permissions = self._aggregate_permissions(user)

        # Create new access token
        settings = get_settings()
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            roles=roles,
            permissions=permissions,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=None,  # Don't issue new refresh token
            expires_in=settings.jwt_expiration_hours * 3600,
        )

    async def logout(
        self,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Logout by revoking refresh token.

        Args:
            refresh_token: Refresh token to revoke
            ip_address: Client IP address
            user_agent: Client user agent
        """
        token_hash = hash_refresh_token(refresh_token)
        token_record = await self.token_repo.get_by_hash(token_hash)

        if token_record:
            # Audit log
            await self.audit_repo.log(
                action="logout",
                resource_type="admin_user",
                resource_id=token_record.user_id,
                admin_user_id=token_record.user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.token_repo.revoke_token(token_record.id)
            await self.session.commit()

    async def logout_all_sessions(self, user_id: UUID) -> int:
        """Logout all sessions for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of sessions revoked
        """
        count = await self.token_repo.revoke_all_for_user(user_id)
        await self.session.commit()
        return count

    async def get_user_info(self, user_id: UUID) -> UserInfo | None:
        """Get user info by ID.

        Args:
            user_id: User UUID

        Returns:
            UserInfo or None
        """
        user = await self.user_repo.get_with_roles(user_id)
        if user is None:
            return None

        roles, permissions = self._aggregate_permissions(user)

        return UserInfo(
            id=user.id,
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
            auth_provider=user.auth_provider,
            is_active=user.is_active,
            require_password_change=user.require_password_change,
            roles=roles,
            permissions=permissions,
            is_superadmin="superadmin" in roles,
            last_login_at=user.last_login_at,
        )

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Change user password.

        Args:
            user_id: User UUID
            current_password: Current password
            new_password: New password
            ip_address: Client IP address
            user_agent: Client user agent

        Raises:
            HTTPException: If validation fails
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password change not available for this account",
            )

        # Verify current password
        if not self.password_service.verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        # Validate new password strength
        is_valid, errors = self.password_service.validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=errors[0],
            )

        # Check password history
        history = await self.user_repo.get_password_history(user_id)
        history.append(user.password_hash)  # Include current password

        if self.password_service.check_password_history(new_password, history):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password was recently used",
            )

        # Update password
        new_hash = self.password_service.hash_password(new_password)
        await self.user_repo.update_password(user_id, new_hash, require_change=False)

        # Revoke all other sessions
        await self.token_repo.revoke_all_for_user(user_id)

        # Audit log
        await self.audit_repo.log(
            action="password_change",
            resource_type="admin_user",
            resource_id=user_id,
            admin_user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

    def _aggregate_permissions(self, user) -> tuple[list[str], list[str]]:
        """Aggregate permissions from user roles.

        Args:
            user: User ORM with roles loaded

        Returns:
            Tuple of (role_codes, permission_codes)
        """
        roles = []
        permissions = set()

        for role in user.roles:
            roles.append(role.code)
            for perm in role.permissions:
                permissions.add(perm.code)

        return roles, sorted(permissions)
