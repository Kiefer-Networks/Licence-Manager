"""Authentication service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.config import get_settings
from licence_api.constants.paths import ADMIN_AVATAR_DIR
from licence_api.models.dto.auth import (
    LoginResponse,
    TokenResponse,
    TotpBackupCodesResponse,
    TotpEnableResponse,
    TotpSetupResponse,
    TotpStatusResponse,
    UserInfo,
)
from licence_api.repositories.audit_repository import AuditRepository
from licence_api.repositories.role_repository import RoleRepository
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.repositories.user_repository import RefreshTokenRepository, UserRepository
from licence_api.repositories.user_notification_preference_repository import UserNotificationPreferenceRepository
from licence_api.security.auth import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from licence_api.security.password import get_password_service
from licence_api.services.totp_service import get_totp_service
from licence_api.utils.file_validation import (
    validate_image_signature,
    get_extension_from_content_type,
)
from licence_api.utils.secure_logging import log_error, log_warning
from licence_api.utils.security_events import log_security_event, SecurityEventType

logger = logging.getLogger(__name__)

MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.token_repo = RefreshTokenRepository(session)
        self.audit_repo = AuditRepository(session)
        self.notification_pref_repo = UserNotificationPreferenceRepository(session)
        self.settings_repo = SettingsRepository(session)
        self.password_service = get_password_service()

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

    async def authenticate_local(
        self,
        email: str,
        password: str,
        totp_code: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> LoginResponse:
        """Authenticate with email and password, optionally with TOTP.

        Args:
            email: User email
            password: User password
            totp_code: TOTP code if 2FA is enabled
            user_agent: User agent string
            ip_address: IP address

        Returns:
            LoginResponse with tokens or totp_required flag

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
            # Log failed login attempt
            log_security_event(
                SecurityEventType.LOGIN_FAILED,
                user_id=user.id,
                user_email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Check if TOTP is enabled
        if user.totp_enabled:
            if not totp_code:
                # TOTP required but not provided
                return LoginResponse(
                    totp_required=True,
                )

            # Verify TOTP code
            totp_valid = await self._verify_totp_code(user.id, totp_code)
            if not totp_valid:
                await self.user_repo.record_failed_login(user.id)
                await self.session.commit()
                log_security_event(
                    SecurityEventType.LOGIN_FAILED,
                    user_id=user.id,
                    user_email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    details={"reason": "invalid_totp"},
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid two-factor authentication code",
                )

        # Successful login
        await self.user_repo.record_successful_login(user.id)
        # Log successful login
        log_security_event(
            SecurityEventType.LOGIN_SUCCESS,
            user_id=user.id,
            user_email=email,
            ip_address=ip_address,
            user_agent=user_agent,
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
            changes={"method": "local", "email": user.email, "totp_used": user.totp_enabled},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

        return LoginResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.jwt_expiration_hours * 3600,
            totp_required=False,
        )

    async def _verify_totp_code(self, user_id: UUID, code: str) -> bool:
        """Verify a TOTP code or backup code.

        Args:
            user_id: User UUID
            code: TOTP code or backup code

        Returns:
            True if code is valid
        """
        totp_data = await self.user_repo.get_totp_data(user_id)
        if totp_data is None:
            return False

        secret_encrypted, backup_codes_encrypted, enabled = totp_data
        if not enabled or not secret_encrypted:
            return False

        totp_service = get_totp_service()

        # Normalize code: remove dashes for backup codes
        normalized_code = code.replace("-", "")

        # Check if it's a 6-digit TOTP code
        if len(normalized_code) == 6 and normalized_code.isdigit():
            secret = totp_service.decrypt_secret(secret_encrypted)
            return totp_service.verify_totp(secret, normalized_code)

        # Check if it's a backup code
        if backup_codes_encrypted and len(normalized_code) == 8:
            is_valid, updated_codes = totp_service.verify_backup_code(
                code, backup_codes_encrypted
            )
            if is_valid and updated_codes:
                # Remove used backup code
                await self.user_repo.update_backup_codes(user_id, updated_codes)
                await self.session.commit()
            return is_valid

        return False

    async def refresh_access_token(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Refresh access token using refresh token with token rotation.

        Implements refresh token rotation for enhanced security:
        - Old refresh token is revoked after single use
        - New refresh token is issued with each refresh
        - Prevents token replay attacks

        Args:
            refresh_token: Refresh token
            user_agent: User agent string for new token
            ip_address: IP address for new token

        Returns:
            New TokenResponse with rotated refresh token

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
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)

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
            refresh_token=raw_refresh,  # Return new rotated refresh token
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
            totp_enabled=user.totp_enabled,
            roles=roles,
            permissions=permissions,
            is_superadmin="superadmin" in roles,
            last_login_at=user.last_login_at,
            language=getattr(user, "language", None) or "en",
            date_format=user.date_format or "DD.MM.YYYY",
            number_format=user.number_format or "de-DE",
            currency=user.currency or "EUR",
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

        # Get password policy from settings
        password_policy = await self._get_password_policy()

        # Validate new password strength against policy
        is_valid, errors = self.password_service.validate_password_strength(
            new_password, policy=password_policy
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=errors[0],
            )

        # Check password history using policy settings
        history = await self.user_repo.get_password_history(user_id)
        history.append(user.password_hash)  # Include current password

        if self.password_service.check_password_history(
            new_password, history, policy=password_policy
        ):
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

        # Security event log
        log_security_event(
            SecurityEventType.PASSWORD_CHANGED,
            user_id=user_id,
            user_email=user.email,
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
        """Update user profile.

        Args:
            user_id: User UUID
            name: New name (None to clear)
            language: Language preference (ISO 639-1)
            date_format: Date format preference
            number_format: Number format locale
            currency: Currency code

        Returns:
            Updated UserInfo

        Raises:
            HTTPException: If user not found
        """
        if name is not None:
            await self.user_repo.update_name(user_id, name if name else None)

        # Update locale preferences if any are provided
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
        """Upload user avatar.

        Args:
            user_id: User UUID
            content: Image content bytes
            content_type: Content type (e.g., image/jpeg)

        Returns:
            Avatar URL

        Raises:
            ValueError: If validation fails
        """
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Invalid file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}")

        if len(content) > MAX_AVATAR_SIZE:
            raise ValueError(f"File too large. Maximum size: {MAX_AVATAR_SIZE // (1024 * 1024)} MB")

        if not validate_image_signature(content, content_type):
            raise ValueError("File content does not match declared file type")

        # Ensure avatar directory exists
        ADMIN_AVATAR_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename
        ext = get_extension_from_content_type(content_type)
        filename = f"{user_id}{ext}"
        file_path = ADMIN_AVATAR_DIR / filename

        # Remove old avatar with different extension
        for old_ext in [".jpg", ".png", ".gif", ".webp"]:
            old_file = ADMIN_AVATAR_DIR / f"{user_id}{old_ext}"
            if old_file.exists() and old_file != file_path:
                try:
                    old_file.unlink()
                except OSError as e:
                    log_warning(logger, "Failed to delete old avatar file", e)

        # Write new avatar
        try:
            file_path.write_bytes(content)
        except Exception as e:
            log_error(logger, "Failed to write avatar file", e)
            raise ValueError("Failed to save avatar")

        # Update picture_url in database
        picture_url = f"/api/v1/auth/avatar/{user_id}"
        await self.user_repo.update_avatar(user_id, picture_url)
        await self.session.commit()

        return picture_url

    async def delete_avatar(self, user_id: UUID) -> None:
        """Delete user avatar.

        Args:
            user_id: User UUID
        """
        # Remove avatar files
        for ext in [".jpg", ".png", ".gif", ".webp"]:
            file_path = ADMIN_AVATAR_DIR / f"{user_id}{ext}"
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError as e:
                    log_warning(logger, "Failed to delete avatar file", e)

        # Clear picture_url in database
        await self.user_repo.update_avatar(user_id, None)
        await self.session.commit()

    # Notification preference methods

    async def get_notification_preferences(self, user_id: UUID) -> list:
        """Get user notification preferences.

        Args:
            user_id: User UUID

        Returns:
            List of notification preference records
        """
        return await self.notification_pref_repo.get_by_user_id(user_id)

    async def update_notification_preferences_bulk(
        self,
        user_id: UUID,
        preferences: list[dict[str, Any]],
    ) -> list:
        """Update notification preferences in bulk.

        Args:
            user_id: User UUID
            preferences: List of preference dicts with event_type, enabled, etc.

        Returns:
            Updated list of notification preference records
        """
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
        """Update a single notification preference.

        Args:
            user_id: User UUID
            event_type: Event type code
            enabled: Enable/disable
            slack_dm: Enable Slack DM
            slack_channel: Slack channel name

        Returns:
            Updated notification preference record
        """
        pref = await self.notification_pref_repo.upsert(
            user_id=user_id,
            event_type=event_type,
            enabled=enabled,
            slack_dm=slack_dm,
            slack_channel=slack_channel,
        )
        await self.session.commit()
        return pref

    # TOTP Two-Factor Authentication Methods

    async def setup_totp(self, user_id: UUID) -> TotpSetupResponse:
        """Initialize TOTP setup for a user.

        Generates a new secret but does not enable TOTP yet.
        User must verify with a code before TOTP is enabled.

        Args:
            user_id: User UUID

        Returns:
            TotpSetupResponse with QR code and secret

        Raises:
            HTTPException: If user not found or TOTP already enabled
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication is already enabled",
            )

        totp_service = get_totp_service()

        # Generate new secret
        secret = totp_service.generate_secret()
        secret_encrypted = totp_service.encrypt_secret(secret)

        # Store encrypted secret (not enabled yet)
        await self.user_repo.setup_totp(user_id, secret_encrypted)
        await self.session.commit()

        # Generate provisioning URI and QR code
        provisioning_uri = totp_service.get_provisioning_uri(secret, user.email)
        qr_code = totp_service.generate_qr_code_data_uri(provisioning_uri)

        return TotpSetupResponse(
            secret=secret,
            qr_code_data_uri=qr_code,
            provisioning_uri=provisioning_uri,
        )

    async def verify_and_enable_totp(
        self,
        user_id: UUID,
        code: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TotpEnableResponse:
        """Verify TOTP code and enable 2FA.

        Args:
            user_id: User UUID
            code: 6-digit TOTP code
            ip_address: Client IP
            user_agent: Client user agent

        Returns:
            TotpEnableResponse with backup codes

        Raises:
            HTTPException: If verification fails
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication is already enabled",
            )

        if not user.totp_secret_encrypted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TOTP setup not initiated. Please start setup first.",
            )

        totp_service = get_totp_service()

        # Decrypt and verify
        secret = totp_service.decrypt_secret(user.totp_secret_encrypted)
        if not totp_service.verify_totp(secret, code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code",
            )

        # Generate backup codes
        backup_codes = totp_service.generate_backup_codes()
        backup_codes_encrypted = totp_service.encrypt_backup_codes(backup_codes)

        # Enable TOTP
        await self.user_repo.enable_totp(user_id, backup_codes_encrypted)

        # Audit log
        await self.audit_repo.log(
            action="totp_enabled",
            resource_type="admin_user",
            resource_id=user_id,
            admin_user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Security event
        log_security_event(
            SecurityEventType.TOTP_ENABLED,
            user_id=user_id,
            user_email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

        return TotpEnableResponse(
            enabled=True,
            backup_codes=backup_codes,
        )

    async def disable_totp(
        self,
        user_id: UUID,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Disable TOTP (requires password verification).

        Args:
            user_id: User UUID
            password: Current password for verification
            ip_address: Client IP
            user_agent: Client user agent

        Raises:
            HTTPException: If password is wrong or TOTP not enabled
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication is not enabled",
            )

        # Verify password
        if not user.password_hash or not self.password_service.verify_password(
            password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password",
            )

        # Disable TOTP
        await self.user_repo.disable_totp(user_id)

        # Audit log
        await self.audit_repo.log(
            action="totp_disabled",
            resource_type="admin_user",
            resource_id=user_id,
            admin_user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Security event
        log_security_event(
            SecurityEventType.TOTP_DISABLED,
            user_id=user_id,
            user_email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

    async def get_totp_status(self, user_id: UUID) -> TotpStatusResponse:
        """Get TOTP status for a user.

        Args:
            user_id: User UUID

        Returns:
            TotpStatusResponse
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        backup_codes_remaining = 0
        if user.totp_enabled and user.totp_backup_codes_encrypted:
            totp_service = get_totp_service()
            hashed_codes = totp_service.decrypt_backup_codes(
                user.totp_backup_codes_encrypted
            )
            backup_codes_remaining = len(hashed_codes)

        return TotpStatusResponse(
            enabled=user.totp_enabled,
            verified_at=user.totp_verified_at,
            backup_codes_remaining=backup_codes_remaining,
        )

    async def regenerate_backup_codes(
        self,
        user_id: UUID,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TotpBackupCodesResponse:
        """Regenerate backup codes (requires password verification).

        Args:
            user_id: User UUID
            password: Current password
            ip_address: Client IP
            user_agent: Client user agent

        Returns:
            TotpBackupCodesResponse with new codes

        Raises:
            HTTPException: If verification fails
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication is not enabled",
            )

        # Verify password
        if not user.password_hash or not self.password_service.verify_password(
            password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password",
            )

        totp_service = get_totp_service()

        # Generate new backup codes
        backup_codes = totp_service.generate_backup_codes()
        backup_codes_encrypted = totp_service.encrypt_backup_codes(backup_codes)

        # Update backup codes
        await self.user_repo.update_backup_codes(user_id, backup_codes_encrypted)

        # Audit log
        await self.audit_repo.log(
            action="totp_backup_codes_regenerated",
            resource_type="admin_user",
            resource_id=user_id,
            admin_user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()

        return TotpBackupCodesResponse(backup_codes=backup_codes)
