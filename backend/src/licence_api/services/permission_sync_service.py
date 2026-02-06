"""Permission sync service for automatic system role updates.

This service synchronizes system roles with current permissions on startup,
ensuring that new permissions are automatically assigned to the appropriate roles.
"""

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    pass

from licence_api.models.orm.permission import PermissionORM
from licence_api.models.orm.role import RoleORM
from licence_api.models.orm.role_permission import RolePermissionORM

logger = logging.getLogger(__name__)


class PermissionSyncService:
    """Synchronizes system roles with current permissions.

    Rules:
    - superadmin: Gets ALL permissions (already handled via has_any_permission in code)
    - admin: Gets ALL permissions EXCEPT system.admin
    - auditor: Gets ONLY *.view and *.export permissions
    """

    # Permissions to exclude from admin role
    ADMIN_EXCLUDE = ["system.admin"]

    # Patterns for auditor role (suffix matching)
    AUDITOR_PATTERNS = [".view", ".export"]

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Database session
        """
        self.session = session

    async def sync_system_roles(self) -> dict[str, int]:
        """Synchronize system roles with current permissions.

        Returns:
            Dict with counts of permissions added per role
        """
        results = {
            "admin_added": 0,
            "auditor_added": 0,
        }

        # Get all permissions
        permissions_result = await self.session.execute(select(PermissionORM))
        all_permissions = list(permissions_result.scalars().all())
        permission_map = {p.code: p.id for p in all_permissions}

        # Get system roles
        roles_result = await self.session.execute(
            select(RoleORM).where(RoleORM.is_system == True)  # noqa: E712
        )
        system_roles = {r.code: r for r in roles_result.scalars().all()}

        # Sync admin role
        if "admin" in system_roles:
            admin_role = system_roles["admin"]
            admin_perms = await self._get_admin_permissions(all_permissions)
            added = await self._sync_role_permissions(admin_role.id, admin_perms)
            results["admin_added"] = added

        # Sync auditor role
        if "auditor" in system_roles:
            auditor_role = system_roles["auditor"]
            auditor_perms = await self._get_auditor_permissions(all_permissions)
            added = await self._sync_role_permissions(auditor_role.id, auditor_perms)
            results["auditor_added"] = added

        await self.session.commit()

        if results["admin_added"] > 0 or results["auditor_added"] > 0:
            logger.info(
                f"Permission sync completed: {results['admin_added']} added to admin, "
                f"{results['auditor_added']} added to auditor"
            )
        else:
            logger.debug("Permission sync: no changes needed")

        return results

    async def _get_admin_permissions(
        self, all_permissions: list[PermissionORM]
    ) -> list[PermissionORM]:
        """Get permissions for admin role (all except excluded).

        Args:
            all_permissions: All available permissions

        Returns:
            List of permissions for admin role
        """
        return [p for p in all_permissions if p.code not in self.ADMIN_EXCLUDE]

    async def _get_auditor_permissions(
        self, all_permissions: list[PermissionORM]
    ) -> list[PermissionORM]:
        """Get permissions for auditor role (view and export only).

        Args:
            all_permissions: All available permissions

        Returns:
            List of permissions for auditor role
        """
        return [
            p
            for p in all_permissions
            if any(p.code.endswith(pattern) for pattern in self.AUDITOR_PATTERNS)
        ]

    async def _sync_role_permissions(
        self, role_id, permissions: list[PermissionORM]
    ) -> int:
        """Sync permissions for a role, adding missing ones.

        Args:
            role_id: Role UUID
            permissions: Permissions that should be assigned

        Returns:
            Number of permissions added
        """
        # Get existing role permissions
        existing_result = await self.session.execute(
            select(RolePermissionORM.permission_id).where(
                RolePermissionORM.role_id == role_id
            )
        )
        existing_perm_ids = set(existing_result.scalars().all())

        # Find missing permissions
        added = 0
        for perm in permissions:
            if perm.id not in existing_perm_ids:
                role_perm = RolePermissionORM(
                    role_id=role_id,
                    permission_id=perm.id,
                )
                self.session.add(role_perm)
                added += 1

        if added > 0:
            await self.session.flush()

        return added


async def sync_system_role_permissions() -> dict[str, int]:
    """Convenience function to sync system roles.

    Called from application startup.

    Returns:
        Dict with counts of permissions added per role
    """
    from licence_api.database import async_session_maker

    async with async_session_maker() as session:
        service = PermissionSyncService(session)
        return await service.sync_system_roles()
