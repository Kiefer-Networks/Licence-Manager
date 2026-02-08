"""Authentication service - Google OAuth only."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.config import get_settings
from licence_api.constants.paths import ADMIN_AVATAR_DIR
from licence_api.models.dto.auth import (
    LoginResponse,
    TokenResponse,
    UserInfo,
)
from licence_api.repositories.audit_repository import AuditRepository
from licence_api.repositories.role_repository import RoleRepository
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.repositories.user_notification_preference_repository import (
    UserNotificationPreferenceRepository,
)
from licence_api.repositories.user_repository import RefreshTokenRepository, UserRepository
from licence_api.security.auth import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from licence_api.utils.file_validation import (
    get_extension_from_content_type,
    validate_image_signature,
)
from licence_api.utils.secure_logging import log_error, log_warning
from licence_api.utils.security_events import SecurityEventType, log_security_event

logger = logging.getLogger(__name__)

MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class AuthService:
    """Service for authentication operations - Google OAuth only."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.token_repo = RefreshTokenRepository(session)
        self.audit_repo = AuditRepository(session)
        self.notification_pref_repo = UserNotificationPreferenceRepository(session)
        self.settings_repo = SettingsRepository(session)

    async def authenticate_google(
        self,
        google_id: str,
        email: str,
        name: str | None = None,
        picture_url: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> LoginResponse:
        """Authenticate with Google OAuth.

        Looks up user by Google ID first, then by email.
        If found by email but not linked, links the Google account.
        User must already exist in the system - unless they are the configured superadmin.
        The superadmin email (SUPERADMIN_EMAIL env var) is auto-created on first login.

        Args:
            google_id: Google user ID (sub claim)
            email: Google email address
            name: Google display name
            picture_url: Google profile picture URL
            user_agent: User agent string
            ip_address: IP address

        Returns:
            LoginResponse with tokens

        Raises:
            HTTPException: If user not found or disabled
        """
        settings = get_settings()
        email_lower = email.lower()

        # First try to find by Google ID
        user = await self.user_repo.get_by_google_id(google_id)

        if user is None:
            # Try to find by email and link the account
            user = await self.user_repo.get_by_email(email_lower)

            if user is None:
                # Check if this is the configured superadmin email - auto-create
                if settings.superadmin_email and email_lower == settings.superadmin_email.lower():
                    user = await self._create_superadmin_user(
                        email=email_lower,
                        google_id=google_id,
                        name=name,
                        picture_url=picture_url,
                    )
                    logger.info(f"Auto-created superadmin user: {email_lower}")
                else:
                    log_security_event(
                        SecurityEventType.LOGIN_FAILED,
                        user_email=email,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=False,
                        details={"reason": "google_user_not_found"},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No account found for this email. Please contact an administrator.",
                    )
            else:
                # Link Google account to existing user
                await self.user_repo.link_google_account(user.id, google_id)

                # Update profile picture from Google (always prefer fresh Google avatar)
                if picture_url:
                    user.picture_url = picture_url
                    await self.user_repo.update_avatar(user.id, picture_url)
                if not user.name and name:
                    user.name = name
                    await self.user_repo.update_name(user.id, name)
        else:
            # User found by Google ID - update profile picture from Google
            if picture_url and user.picture_url != picture_url:
                user.picture_url = picture_url
                await self.user_repo.update_avatar(user.id, picture_url)

        # Ensure superadmin role for configured superadmin email
        if settings.superadmin_email and email_lower == settings.superadmin_email.lower():
            await self._ensure_superadmin_role(user)

        # Check if account is active
        if not user.is_active:
            log_security_event(
                SecurityEventType.LOGIN_FAILED,
                user_id=user.id,
                user_email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                details={"reason": "account_disabled"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        # Successful login
        await self.user_repo.record_successful_login(user.id)
        log_security_event(
            SecurityEventType.LOGIN_SUCCESS,
            user_id=user.id,
            user_email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"method": "google"},
        )

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
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)

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

        return LoginResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.jwt_expiration_hours * 3600,
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Refresh access token using refresh token with token rotation."""
        token_hash = hash_refresh_token(refresh_token)
        token_record = await self.token_repo.get_by_hash(token_hash)

        if token_record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if token_record.expires_at < datetime.now(UTC):
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

        # Revoke the old refresh token (one-time use)
        await self.token_repo.revoke_token(token_record.id)

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

        # Create new refresh token (rotation)
        raw_refresh, refresh_hash = create_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)

        await self.token_repo.create_token(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent or token_record.user_agent,
            ip_address=ip_address or token_record.ip_address,
        )

        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.jwt_expiration_hours * 3600,
        )

    async def logout(
        self,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Logout by revoking refresh token."""
        token_hash = hash_refresh_token(refresh_token)
        token_record = await self.token_repo.get_by_hash(token_hash)

        if token_record:
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
        """Logout all sessions for a user."""
        count = await self.token_repo.revoke_all_for_user(user_id)
        await self.session.commit()
        return count

    async def get_user_info(self, user_id: UUID) -> UserInfo | None:
        """Get user info by ID."""
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
            roles=roles,
            permissions=permissions,
            is_superadmin="superadmin" in roles,
            last_login_at=user.last_login_at,
            language=getattr(user, "language", None) or "en",
            date_format=user.date_format or "DD.MM.YYYY",
            number_format=user.number_format or "de-DE",
            currency=user.currency or "EUR",
        )

    def _aggregate_permissions(self, user) -> tuple[list[str], list[str]]:
        """Aggregate permissions from user roles."""
        roles = []
        permissions = set()

        for role in user.roles:
            roles.append(role.code)
            for perm in role.permissions:
                permissions.add(perm.code)

        return roles, sorted(permissions)

    async def _create_superadmin_user(
        self,
        email: str,
        google_id: str,
        name: str | None = None,
        picture_url: str | None = None,
    ):
        """Create a new superadmin user.

        Called when the configured SUPERADMIN_EMAIL logs in for the first time.
        """
        from licence_api.models.orm.admin_user import AdminUserORM

        # Create the user
        user = AdminUserORM(
            email=email,
            name=name,
            picture_url=picture_url,
            auth_provider="google",
            google_id=google_id,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()

        # Assign superadmin role
        superadmin_role = await self.role_repo.get_by_code("superadmin")
        if superadmin_role:
            await self.user_repo.add_role(user.id, superadmin_role.id)

        return user

    async def _ensure_superadmin_role(self, user) -> None:
        """Ensure user has the superadmin role.

        Called on every login for the configured SUPERADMIN_EMAIL to ensure
        they always have superadmin privileges.
        """
        has_superadmin = any(role.code == "superadmin" for role in user.roles)
        if not has_superadmin:
            superadmin_role = await self.role_repo.get_by_code("superadmin")
            if superadmin_role:
                await self.user_repo.add_role(user.id, superadmin_role.id)
                # Refresh user's roles
                user = await self.user_repo.get_with_roles(user.id)
                logger.info(f"Auto-assigned superadmin role to: {user.email}")

    # Profile management methods

    async def update_profile(
        self,
        user_id: UUID,
        name: str | None = None,
        language: str | None = None,
        date_format: str | None = None,
        number_format: str | None = None,
        currency: str | None = None,
    ) -> UserInfo:
        """Update user profile."""
        if name is not None:
            await self.user_repo.update_name(user_id, name if name else None)

        has_locale_update = any(
            x is not None for x in [language, date_format, number_format, currency]
        )
        if has_locale_update:
            await self.user_repo.update_locale_preferences(
                user_id,
                language=language,
                date_format=date_format,
                number_format=number_format,
                currency=currency,
            )

        await self.session.commit()

        user_info = await self.get_user_info(user_id)
        if user_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user_info

    async def upload_avatar(
        self,
        user_id: UUID,
        content: bytes,
        content_type: str,
    ) -> str:
        """Upload user avatar."""
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Invalid file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}")

        if len(content) > MAX_AVATAR_SIZE:
            raise ValueError(f"File too large. Maximum size: {MAX_AVATAR_SIZE // (1024 * 1024)} MB")

        if not validate_image_signature(content, content_type):
            raise ValueError("File content does not match declared file type")

        ADMIN_AVATAR_DIR.mkdir(parents=True, exist_ok=True)

        ext = get_extension_from_content_type(content_type)
        filename = f"{user_id}{ext}"
        file_path = ADMIN_AVATAR_DIR / filename

        for old_ext in [".jpg", ".png", ".gif", ".webp"]:
            old_file = ADMIN_AVATAR_DIR / f"{user_id}{old_ext}"
            if old_file.exists() and old_file != file_path:
                try:
                    old_file.unlink()
                except OSError as e:
                    log_warning(logger, "Failed to delete old avatar file", e)

        try:
            file_path.write_bytes(content)
        except Exception as e:
            log_error(logger, "Failed to write avatar file", e)
            raise ValueError("Failed to save avatar")

        picture_url = f"/api/v1/auth/avatar/{user_id}"
        await self.user_repo.update_avatar(user_id, picture_url)
        await self.session.commit()

        return picture_url

    async def delete_avatar(self, user_id: UUID) -> None:
        """Delete user avatar."""
        for ext in [".jpg", ".png", ".gif", ".webp"]:
            file_path = ADMIN_AVATAR_DIR / f"{user_id}{ext}"
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError as e:
                    log_warning(logger, "Failed to delete avatar file", e)

        await self.user_repo.update_avatar(user_id, None)
        await self.session.commit()

    # Notification preference methods

    async def get_notification_preferences(self, user_id: UUID) -> list:
        """Get user notification preferences."""
        return await self.notification_pref_repo.get_by_user_id(user_id)

    async def update_notification_preferences_bulk(
        self,
        user_id: UUID,
        preferences: list[dict[str, Any]],
    ) -> list:
        """Update notification preferences in bulk."""
        prefs = await self.notification_pref_repo.bulk_upsert(user_id, preferences)
        await self.session.commit()
        return prefs

    async def update_notification_preference(
        self,
        user_id: UUID,
        event_type: str,
        enabled: bool | None = None,
        slack_dm: bool | None = None,
        slack_channel: str | None = None,
    ):
        """Update a single notification preference."""
        pref = await self.notification_pref_repo.upsert(
            user_id=user_id,
            event_type=event_type,
            enabled=enabled,
            slack_dm=slack_dm,
            slack_channel=slack_channel,
        )
        await self.session.commit()
        return pref
