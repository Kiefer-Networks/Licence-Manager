"""Admin user repository."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from licence_api.models.orm.admin_user import AdminUserORM
from licence_api.models.orm.password_history import PasswordHistoryORM
from licence_api.models.orm.refresh_token import RefreshTokenORM
from licence_api.models.orm.role import RoleORM
from licence_api.models.orm.user_role import UserRoleORM
from licence_api.repositories.base import BaseRepository


class UserRepository(BaseRepository[AdminUserORM]):
    """Repository for admin user operations."""

    model = AdminUserORM

    async def get_by_email(self, email: str) -> AdminUserORM | None:
        """Get admin user by email with roles loaded.

        Args:
            email: User email address

        Returns:
            AdminUserORM or None if not found
        """
        result = await self.session.execute(
            select(AdminUserORM)
            .options(
                selectinload(AdminUserORM.roles).selectinload(RoleORM.permissions)
            )
            .where(AdminUserORM.email == email)
        )
        return result.scalar_one_or_none()

    async def get_with_roles(self, user_id: UUID) -> AdminUserORM | None:
        """Get user with roles and permissions loaded.

        Args:
            user_id: User UUID

        Returns:
            AdminUserORM with roles or None
        """
        result = await self.session.execute(
            select(AdminUserORM)
            .options(
                selectinload(AdminUserORM.roles).selectinload(RoleORM.permissions)
            )
            .where(AdminUserORM.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all_with_roles(self) -> list[AdminUserORM]:
        """Get all users with roles loaded.

        Returns:
            List of AdminUserORM with roles
        """
        result = await self.session.execute(
            select(AdminUserORM)
            .options(
                selectinload(AdminUserORM.roles).selectinload(RoleORM.permissions)
            )
            .order_by(AdminUserORM.email)
        )
        return list(result.scalars().all())

    async def create_user(
        self,
        email: str,
        password_hash: str | None = None,
        name: str | None = None,
        picture_url: str | None = None,
        auth_provider: str = "local",
        require_password_change: bool = False,
        language: str = "en",
    ) -> AdminUserORM:
        """Create a new user.

        Args:
            email: User email
            password_hash: Hashed password (for local auth)
            name: User name
            picture_url: Profile picture URL
            auth_provider: Authentication provider
            require_password_change: Whether user must change password
            language: ISO 639-1 language code for email notifications

        Returns:
            Created AdminUserORM
        """
        user = await self.create(
            email=email,
            password_hash=password_hash,
            name=name,
            picture_url=picture_url,
            auth_provider=auth_provider,
            require_password_change=require_password_change,
            password_changed_at=datetime.now(timezone.utc) if password_hash else None,
            language=language,
        )
        return user

    async def update_password(
        self,
        user_id: UUID,
        password_hash: str,
        require_change: bool = False,
    ) -> AdminUserORM | None:
        """Update user password.

        Args:
            user_id: User UUID
            password_hash: New hashed password
            require_change: Whether to require password change

        Returns:
            Updated AdminUserORM or None
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        # Store old password in history
        if user.password_hash:
            self.session.add(
                PasswordHistoryORM(
                    user_id=user_id,
                    password_hash=user.password_hash,
                )
            )

        user.password_hash = password_hash
        user.password_changed_at = datetime.now(timezone.utc)
        user.require_password_change = require_change
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_password_history(
        self,
        user_id: UUID,
        limit: int = 5,
    ) -> list[str]:
        """Get password history for a user.

        Args:
            user_id: User UUID
            limit: Number of passwords to retrieve

        Returns:
            List of password hashes
        """
        result = await self.session.execute(
            select(PasswordHistoryORM.password_hash)
            .where(PasswordHistoryORM.user_id == user_id)
            .order_by(PasswordHistoryORM.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def record_failed_login(self, user_id: UUID) -> AdminUserORM | None:
        """Record a failed login attempt.

        Args:
            user_id: User UUID

        Returns:
            Updated AdminUserORM or None
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.is_locked = True
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def record_successful_login(self, user_id: UUID) -> AdminUserORM | None:
        """Record a successful login.

        Args:
            user_id: User UUID

        Returns:
            Updated AdminUserORM or None
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.failed_login_attempts = 0
        user.last_login_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def unlock_user(self, user_id: UUID) -> AdminUserORM | None:
        """Unlock a user account.

        Args:
            user_id: User UUID

        Returns:
            Updated AdminUserORM or None
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def set_roles(
        self,
        user_id: UUID,
        role_ids: list[UUID],
        assigned_by: UUID | None = None,
    ) -> None:
        """Set roles for a user (replaces existing).

        Args:
            user_id: User UUID
            role_ids: List of role UUIDs
            assigned_by: UUID of user assigning roles
        """
        # Delete existing roles
        await self.session.execute(
            delete(UserRoleORM).where(UserRoleORM.user_id == user_id)
        )

        # Add new roles
        for role_id in role_ids:
            self.session.add(
                UserRoleORM(
                    user_id=user_id,
                    role_id=role_id,
                    assigned_by=assigned_by,
                )
            )

        await self.session.flush()

    async def add_role(
        self,
        user_id: UUID,
        role_id: UUID,
        assigned_by: UUID | None = None,
    ) -> None:
        """Add a role to a user.

        Args:
            user_id: User UUID
            role_id: Role UUID
            assigned_by: UUID of user assigning role
        """
        self.session.add(
            UserRoleORM(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by,
            )
        )
        await self.session.flush()

    async def remove_role(self, user_id: UUID, role_id: UUID) -> None:
        """Remove a role from a user.

        Args:
            user_id: User UUID
            role_id: Role UUID
        """
        await self.session.execute(
            delete(UserRoleORM)
            .where(UserRoleORM.user_id == user_id)
            .where(UserRoleORM.role_id == role_id)
        )

    async def count_by_role(self, role_code: str) -> int:
        """Count users with a specific role.

        Args:
            role_code: Role code

        Returns:
            Number of users with role
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(UserRoleORM)
            .join(RoleORM, UserRoleORM.role_id == RoleORM.id)
            .where(RoleORM.code == role_code)
        )
        return result.scalar_one()

    async def count_active_users(self) -> int:
        """Count active users.

        Returns:
            Number of active users
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(AdminUserORM)
            .where(AdminUserORM.is_active == True)
        )
        return result.scalar_one()

    async def get_emails_by_ids(self, user_ids: set[UUID]) -> dict[UUID, str]:
        """Get email addresses for multiple user IDs.

        Args:
            user_ids: Set of user UUIDs

        Returns:
            Dict mapping user ID to email address
        """
        if not user_ids:
            return {}

        result = await self.session.execute(
            select(AdminUserORM.id, AdminUserORM.email).where(
                AdminUserORM.id.in_(user_ids)
            )
        )
        return {row.id: row.email for row in result.all()}

    async def get_email_by_id(self, user_id: UUID) -> str | None:
        """Get email address for a single user ID.

        Args:
            user_id: User UUID

        Returns:
            Email address or None if not found
        """
        result = await self.session.execute(
            select(AdminUserORM.email).where(AdminUserORM.id == user_id)
        )
        row = result.first()
        return row.email if row else None

    async def update_name(self, user_id: UUID, name: str | None) -> AdminUserORM | None:
        """Update user's display name.

        Args:
            user_id: User UUID
            name: New name (or None to clear)

        Returns:
            Updated AdminUserORM or None if not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.name = name
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_avatar(self, user_id: UUID, avatar_url: str | None) -> AdminUserORM | None:
        """Update user's avatar URL.

        Args:
            user_id: User UUID
            avatar_url: New avatar URL (or None to clear)

        Returns:
            Updated AdminUserORM or None if not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.picture_url = avatar_url
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_locale_preferences(
        self,
        user_id: UUID,
        language: str | None = None,
        date_format: str | None = None,
        number_format: str | None = None,
        currency: str | None = None,
    ) -> AdminUserORM | None:
        """Update user's locale preferences.

        Args:
            user_id: User UUID
            language: Language code (e.g., en, de)
            date_format: Date format (e.g., DD.MM.YYYY, MM/DD/YYYY)
            number_format: Number format locale (e.g., de-DE, en-US)
            currency: Currency code (e.g., EUR, USD)

        Returns:
            Updated AdminUserORM or None if not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        if language is not None:
            user.language = language
        if date_format is not None:
            user.date_format = date_format
        if number_format is not None:
            user.number_format = number_format
        if currency is not None:
            user.currency = currency

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user and clean up related data.

        Deletes the user, their roles, and tokens.

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False if not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False

        # Delete user roles
        await self.session.execute(
            delete(UserRoleORM).where(UserRoleORM.user_id == user_id)
        )

        # Delete refresh tokens
        await self.session.execute(
            delete(RefreshTokenORM).where(RefreshTokenORM.user_id == user_id)
        )

        # Delete password history
        await self.session.execute(
            delete(PasswordHistoryORM).where(PasswordHistoryORM.user_id == user_id)
        )

        # Delete the user
        await self.session.delete(user)
        await self.session.flush()
        return True

    # TOTP Two-Factor Authentication Methods

    async def setup_totp(
        self,
        user_id: UUID,
        secret_encrypted: bytes,
    ) -> AdminUserORM | None:
        """Store TOTP secret for setup (not yet enabled).

        Args:
            user_id: User UUID
            secret_encrypted: Encrypted TOTP secret

        Returns:
            Updated AdminUserORM or None if not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.totp_secret_encrypted = secret_encrypted
        # Don't enable yet - requires verification
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def enable_totp(
        self,
        user_id: UUID,
        backup_codes_encrypted: bytes,
    ) -> AdminUserORM | None:
        """Enable TOTP after successful verification.

        Args:
            user_id: User UUID
            backup_codes_encrypted: Encrypted backup codes

        Returns:
            Updated AdminUserORM or None if not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.totp_enabled = True
        user.totp_verified_at = datetime.now(timezone.utc)
        user.totp_backup_codes_encrypted = backup_codes_encrypted
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def disable_totp(self, user_id: UUID) -> AdminUserORM | None:
        """Disable TOTP and clear secret.

        Args:
            user_id: User UUID

        Returns:
            Updated AdminUserORM or None if not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.totp_enabled = False
        user.totp_secret_encrypted = None
        user.totp_verified_at = None
        user.totp_backup_codes_encrypted = None
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_backup_codes(
        self,
        user_id: UUID,
        backup_codes_encrypted: bytes,
    ) -> AdminUserORM | None:
        """Update backup codes (after using one or regenerating).

        Args:
            user_id: User UUID
            backup_codes_encrypted: New encrypted backup codes

        Returns:
            Updated AdminUserORM or None if not found
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.totp_backup_codes_encrypted = backup_codes_encrypted
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_totp_data(self, user_id: UUID) -> tuple[bytes | None, bytes | None, bool] | None:
        """Get TOTP data for a user.

        Args:
            user_id: User UUID

        Returns:
            Tuple of (secret_encrypted, backup_codes_encrypted, enabled) or None
        """
        result = await self.session.execute(
            select(
                AdminUserORM.totp_secret_encrypted,
                AdminUserORM.totp_backup_codes_encrypted,
                AdminUserORM.totp_enabled,
            ).where(AdminUserORM.id == user_id)
        )
        row = result.first()
        if row is None:
            return None
        return row.totp_secret_encrypted, row.totp_backup_codes_encrypted, row.totp_enabled


class RefreshTokenRepository(BaseRepository[RefreshTokenORM]):
    """Repository for refresh token operations."""

    model = RefreshTokenORM

    async def get_by_hash(self, token_hash: str) -> RefreshTokenORM | None:
        """Get refresh token by hash.

        Args:
            token_hash: Token hash

        Returns:
            RefreshTokenORM or None
        """
        result = await self.session.execute(
            select(RefreshTokenORM)
            .options(selectinload(RefreshTokenORM.user))
            .where(RefreshTokenORM.token_hash == token_hash)
            .where(RefreshTokenORM.revoked_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshTokenORM:
        """Create a refresh token.

        Args:
            user_id: User UUID
            token_hash: Hashed token
            expires_at: Expiration datetime
            user_agent: User agent string
            ip_address: IP address

        Returns:
            Created RefreshTokenORM
        """
        return await self.create(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def revoke_token(self, token_id: UUID) -> None:
        """Revoke a refresh token.

        Args:
            token_id: Token UUID
        """
        token = await self.get_by_id(token_id)
        if token:
            token.revoked_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        """Revoke all refresh tokens for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of tokens revoked
        """
        result = await self.session.execute(
            select(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == user_id)
            .where(RefreshTokenORM.revoked_at.is_(None))
        )
        tokens = list(result.scalars().all())

        now = datetime.now(timezone.utc)
        for token in tokens:
            token.revoked_at = now

        await self.session.flush()
        return len(tokens)

    async def get_active_sessions(self, user_id: UUID) -> list[RefreshTokenORM]:
        """Get active sessions for a user.

        Args:
            user_id: User UUID

        Returns:
            List of active RefreshTokenORM
        """
        result = await self.session.execute(
            select(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == user_id)
            .where(RefreshTokenORM.revoked_at.is_(None))
            .where(RefreshTokenORM.expires_at > datetime.now(timezone.utc))
            .order_by(RefreshTokenORM.created_at.desc())
        )
        return list(result.scalars().all())

    async def cleanup_expired(self) -> int:
        """Delete expired tokens.

        Returns:
            Number of tokens deleted
        """
        result = await self.session.execute(
            delete(RefreshTokenORM)
            .where(RefreshTokenORM.expires_at < datetime.now(timezone.utc))
        )
        await self.session.flush()
        return result.rowcount
