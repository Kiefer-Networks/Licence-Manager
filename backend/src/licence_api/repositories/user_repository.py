"""Admin user repository."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.admin_user import AdminUserORM
from licence_api.repositories.base import BaseRepository


class UserRepository(BaseRepository[AdminUserORM]):
    """Repository for admin user operations."""

    model = AdminUserORM

    async def get_by_email(self, email: str) -> AdminUserORM | None:
        """Get admin user by email.

        Args:
            email: User email address

        Returns:
            AdminUserORM or None if not found
        """
        result = await self.session.execute(
            select(AdminUserORM).where(AdminUserORM.email == email)
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        email: str,
        name: str | None = None,
        picture_url: str | None = None,
        role: str = "viewer",
    ) -> AdminUserORM:
        """Create or update an admin user.

        Args:
            email: User email
            name: User name
            picture_url: Profile picture URL
            role: User role

        Returns:
            Created or updated AdminUserORM
        """
        existing = await self.get_by_email(email)

        if existing:
            existing.name = name
            existing.picture_url = picture_url
            existing.last_login_at = datetime.now(timezone.utc)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        return await self.create(
            email=email,
            name=name,
            picture_url=picture_url,
            role=role,
            last_login_at=datetime.now(timezone.utc),
        )

    async def count_admins(self) -> int:
        """Count users with admin role.

        Returns:
            Number of admin users
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count()).select_from(AdminUserORM).where(AdminUserORM.role == "admin")
        )
        return result.scalar_one()
