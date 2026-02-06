"""Role repository."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from licence_api.models.orm.role import RoleORM
from licence_api.models.orm.role_permission import RolePermissionORM
from licence_api.models.orm.user_role import UserRoleORM
from licence_api.repositories.base import BaseRepository


class RoleRepository(BaseRepository[RoleORM]):
    """Repository for role operations."""

    model = RoleORM

    async def get_by_code(self, code: str) -> RoleORM | None:
        """Get role by code.

        Args:
            code: Role code

        Returns:
            RoleORM or None if not found
        """
        result = await self.session.execute(
            select(RoleORM).options(selectinload(RoleORM.permissions)).where(RoleORM.code == code)
        )
        return result.scalar_one_or_none()

    async def get_with_permissions(self, role_id: UUID) -> RoleORM | None:
        """Get role with permissions loaded.

        Args:
            role_id: Role UUID

        Returns:
            RoleORM with permissions or None
        """
        result = await self.session.execute(
            select(RoleORM).options(selectinload(RoleORM.permissions)).where(RoleORM.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_all_with_permissions(self) -> list[RoleORM]:
        """Get all roles with permissions.

        Returns:
            List of RoleORM with permissions
        """
        result = await self.session.execute(
            select(RoleORM)
            .options(selectinload(RoleORM.permissions))
            .order_by(RoleORM.priority.desc())
        )
        return list(result.scalars().all())

    async def get_by_codes(self, codes: list[str]) -> list[RoleORM]:
        """Get roles by codes.

        Args:
            codes: List of role codes

        Returns:
            List of RoleORM
        """
        result = await self.session.execute(
            select(RoleORM)
            .options(selectinload(RoleORM.permissions))
            .where(RoleORM.code.in_(codes))
        )
        return list(result.scalars().all())

    async def create_role(
        self,
        code: str,
        name: str,
        description: str | None = None,
        is_system: bool = False,
        priority: int = 0,
    ) -> RoleORM:
        """Create a new role.

        Args:
            code: Role code
            name: Role name
            description: Role description
            is_system: Whether this is a system role
            priority: Role priority

        Returns:
            Created RoleORM
        """
        return await self.create(
            code=code,
            name=name,
            description=description,
            is_system=is_system,
            priority=priority,
        )

    async def set_permissions(
        self,
        role_id: UUID,
        permission_ids: list[UUID],
    ) -> None:
        """Set permissions for a role (replaces existing).

        Args:
            role_id: Role UUID
            permission_ids: List of permission UUIDs
        """
        # Delete existing permissions
        await self.session.execute(
            delete(RolePermissionORM).where(RolePermissionORM.role_id == role_id)
        )

        # Add new permissions
        for perm_id in permission_ids:
            self.session.add(RolePermissionORM(role_id=role_id, permission_id=perm_id))

        await self.session.flush()

    async def add_permission(self, role_id: UUID, permission_id: UUID) -> None:
        """Add a permission to a role.

        Args:
            role_id: Role UUID
            permission_id: Permission UUID
        """
        self.session.add(RolePermissionORM(role_id=role_id, permission_id=permission_id))
        await self.session.flush()

    async def remove_permission(self, role_id: UUID, permission_id: UUID) -> None:
        """Remove a permission from a role.

        Args:
            role_id: Role UUID
            permission_id: Permission UUID
        """
        await self.session.execute(
            delete(RolePermissionORM)
            .where(RolePermissionORM.role_id == role_id)
            .where(RolePermissionORM.permission_id == permission_id)
        )

    async def count_users_with_role(self, role_id: UUID) -> int:
        """Count users assigned to a role.

        Args:
            role_id: Role UUID

        Returns:
            Number of users with this role
        """
        result = await self.session.execute(
            select(func.count(UserRoleORM.user_id)).where(UserRoleORM.role_id == role_id)
        )
        return result.scalar_one()

    async def delete_role(self, role_id: UUID) -> bool:
        """Delete a non-system role.

        Args:
            role_id: Role UUID

        Returns:
            True if deleted
        """
        role = await self.get_by_id(role_id)
        if role is None or role.is_system:
            return False

        await self.session.delete(role)
        await self.session.flush()
        return True
