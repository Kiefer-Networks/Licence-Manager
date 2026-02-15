"""Admin user repository - Google OAuth only."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import selectinload

from licence_api.models.orm.admin_user import AdminUserORM
from licence_api.models.orm.refresh_token import RefreshTokenORM
from licence_api.models.orm.role import RoleORM
from licence_api.models.orm.user_role import UserRoleORM
from licence_api.repositories.base import BaseRepository


class UserRepository(BaseRepository[AdminUserORM]):
    """Repository for admin user operations - Google OAuth only."""

    model = AdminUserORM

    async def get_by_email(self, email: str) -> AdminUserORM | None:
        """Get admin user by email with roles loaded."""
        result = await self.session.execute(
            select(AdminUserORM)
            .options(selectinload(AdminUserORM.roles).selectinload(RoleORM.permissions))
            .where(AdminUserORM.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> AdminUserORM | None:
        """Get admin user by Google ID with roles loaded."""
        result = await self.session.execute(
            select(AdminUserORM)
            .options(selectinload(AdminUserORM.roles).selectinload(RoleORM.permissions))
            .where(AdminUserORM.google_id == google_id)
        )
        return result.scalar_one_or_none()

    async def link_google_account(self, user_id: UUID, google_id: str) -> None:
        """Link a Google account to an existing user."""
        await self.session.execute(
            update(AdminUserORM)
            .where(AdminUserORM.id == user_id)
            .values(google_id=google_id, auth_provider="google")
        )

    async def get_with_roles(self, user_id: UUID) -> AdminUserORM | None:
        """Get user with roles and permissions loaded."""
        result = await self.session.execute(
            select(AdminUserORM)
            .options(selectinload(AdminUserORM.roles).selectinload(RoleORM.permissions))
            .where(AdminUserORM.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all_with_roles(self) -> list[AdminUserORM]:
        """Get all users with roles loaded."""
        result = await self.session.execute(
            select(AdminUserORM)
            .options(selectinload(AdminUserORM.roles).selectinload(RoleORM.permissions))
            .order_by(AdminUserORM.email)
        )
        return list(result.scalars().all())

    async def create_user(
        self,
        email: str,
        password_hash: str | None = None,  # Kept for backwards compat, ignored
        name: str | None = None,
        picture_url: str | None = None,
        auth_provider: str = "google",
        require_password_change: bool = False,  # Kept for backwards compat, ignored
        language: str = "en",
    ) -> AdminUserORM:
        """Create a new user for Google OAuth authentication."""
        user = await self.create(
            email=email,
            name=name,
            picture_url=picture_url,
            auth_provider="google",
            language=language,
        )
        return user

    async def record_successful_login(self, user_id: UUID) -> AdminUserORM | None:
        """Record a successful login."""
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.last_login_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def set_roles(
        self,
        user_id: UUID,
        role_ids: list[UUID],
        assigned_by: UUID | None = None,
    ) -> None:
        """Set roles for a user (replaces existing)."""
        await self.session.execute(delete(UserRoleORM).where(UserRoleORM.user_id == user_id))

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
        """Add a role to a user."""
        self.session.add(
            UserRoleORM(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by,
            )
        )
        await self.session.flush()

    async def remove_role(self, user_id: UUID, role_id: UUID) -> None:
        """Remove a role from a user."""
        await self.session.execute(
            delete(UserRoleORM)
            .where(UserRoleORM.user_id == user_id)
            .where(UserRoleORM.role_id == role_id)
        )

    async def count_by_role(self, role_code: str) -> int:
        """Count users with a specific role."""
        result = await self.session.execute(
            select(func.count())
            .select_from(UserRoleORM)
            .join(RoleORM, UserRoleORM.role_id == RoleORM.id)
            .where(RoleORM.code == role_code)
        )
        return result.scalar_one()

    async def count_active_users(self) -> int:
        """Count active users."""
        result = await self.session.execute(
            select(func.count()).select_from(AdminUserORM).where(AdminUserORM.is_active == True)
        )
        return result.scalar_one()

    async def get_names_by_ids(self, user_ids: list[UUID]) -> dict[UUID, str]:
        """Get display names (or email fallback) for multiple user IDs.

        Args:
            user_ids: List of user UUIDs

        Returns:
            Dict mapping user ID to display name (or email if name is empty)
        """
        if not user_ids:
            return {}

        result = await self.session.execute(
            select(AdminUserORM).where(AdminUserORM.id.in_(user_ids))
        )
        return {admin.id: admin.name or admin.email for admin in result.scalars().all()}

    async def get_emails_by_ids(self, user_ids: set[UUID]) -> dict[UUID, str]:
        """Get email addresses for multiple user IDs."""
        if not user_ids:
            return {}

        result = await self.session.execute(
            select(AdminUserORM.id, AdminUserORM.email).where(AdminUserORM.id.in_(user_ids))
        )
        return {row.id: row.email for row in result.all()}

    async def get_email_by_id(self, user_id: UUID) -> str | None:
        """Get email address for a single user ID."""
        result = await self.session.execute(
            select(AdminUserORM.email).where(AdminUserORM.id == user_id)
        )
        row = result.first()
        return row.email if row else None

    async def update_name(self, user_id: UUID, name: str | None) -> AdminUserORM | None:
        """Update user's display name."""
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.name = name
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_avatar(self, user_id: UUID, avatar_url: str | None) -> AdminUserORM | None:
        """Update user's avatar URL."""
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
        """Update user's locale preferences."""
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
        """Delete a user and clean up related data."""
        user = await self.get_by_id(user_id)
        if user is None:
            return False

        # Delete user roles
        await self.session.execute(delete(UserRoleORM).where(UserRoleORM.user_id == user_id))

        # Delete refresh tokens
        await self.session.execute(
            delete(RefreshTokenORM).where(RefreshTokenORM.user_id == user_id)
        )

        # Delete the user
        await self.session.delete(user)
        await self.session.flush()
        return True


class RefreshTokenRepository(BaseRepository[RefreshTokenORM]):
    """Repository for refresh token operations."""

    model = RefreshTokenORM

    async def get_by_hash(self, token_hash: str) -> RefreshTokenORM | None:
        """Get refresh token by hash."""
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
        """Create a refresh token."""
        return await self.create(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def revoke_token(self, token_id: UUID) -> None:
        """Revoke a refresh token."""
        token = await self.get_by_id(token_id)
        if token:
            token.revoked_at = datetime.now(UTC)
            await self.session.flush()

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        """Revoke all refresh tokens for a user."""
        result = await self.session.execute(
            select(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == user_id)
            .where(RefreshTokenORM.revoked_at.is_(None))
        )
        tokens = list(result.scalars().all())

        now = datetime.now(UTC)
        for token in tokens:
            token.revoked_at = now

        await self.session.flush()
        return len(tokens)

    async def get_active_sessions(self, user_id: UUID) -> list[RefreshTokenORM]:
        """Get active sessions for a user."""
        result = await self.session.execute(
            select(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == user_id)
            .where(RefreshTokenORM.revoked_at.is_(None))
            .where(RefreshTokenORM.expires_at > datetime.now(UTC))
            .order_by(RefreshTokenORM.created_at.desc())
        )
        return list(result.scalars().all())

    async def cleanup_expired(self) -> int:
        """Delete expired tokens."""
        result = await self.session.execute(
            delete(RefreshTokenORM).where(RefreshTokenORM.expires_at < datetime.now(UTC))
        )
        await self.session.flush()
        return result.rowcount
