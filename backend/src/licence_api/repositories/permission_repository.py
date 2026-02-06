"""Permission repository."""

from sqlalchemy import select

from licence_api.models.orm.permission import PermissionORM
from licence_api.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[PermissionORM]):
    """Repository for permission operations."""

    model = PermissionORM

    async def get_by_code(self, code: str) -> PermissionORM | None:
        """Get permission by code.

        Args:
            code: Permission code

        Returns:
            PermissionORM or None if not found
        """
        result = await self.session.execute(select(PermissionORM).where(PermissionORM.code == code))
        return result.scalar_one_or_none()

    async def get_by_codes(self, codes: list[str]) -> list[PermissionORM]:
        """Get permissions by codes.

        Args:
            codes: List of permission codes

        Returns:
            List of PermissionORM
        """
        result = await self.session.execute(
            select(PermissionORM).where(PermissionORM.code.in_(codes))
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[PermissionORM]:
        """Get all permissions.

        Returns:
            List of PermissionORM
        """
        result = await self.session.execute(
            select(PermissionORM).order_by(PermissionORM.category, PermissionORM.code)
        )
        return list(result.scalars().all())

    async def get_by_category(self, category: str) -> list[PermissionORM]:
        """Get permissions by category.

        Args:
            category: Permission category

        Returns:
            List of PermissionORM
        """
        result = await self.session.execute(
            select(PermissionORM)
            .where(PermissionORM.category == category)
            .order_by(PermissionORM.code)
        )
        return list(result.scalars().all())

    async def get_categories(self) -> list[str]:
        """Get all unique categories.

        Returns:
            List of category names
        """
        result = await self.session.execute(
            select(PermissionORM.category).distinct().order_by(PermissionORM.category)
        )
        return list(result.scalars().all())
