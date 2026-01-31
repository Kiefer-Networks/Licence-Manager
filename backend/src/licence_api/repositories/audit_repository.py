"""Audit log repository."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.audit_log import AuditLogORM
from licence_api.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLogORM]):
    """Repository for audit log operations."""

    model = AuditLogORM

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: UUID | None = None,
        admin_user_id: UUID | None = None,
        changes: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLogORM:
        """Create an audit log entry.

        Args:
            action: Action performed (create, update, delete, etc.)
            resource_type: Type of resource affected
            resource_id: ID of affected resource
            admin_user_id: ID of admin user who performed action
            changes: Dict of changes made
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created AuditLogORM
        """
        log_entry = AuditLogORM(
            id=uuid4(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            admin_user_id=admin_user_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry

    async def get_by_resource(
        self,
        resource_type: str,
        resource_id: UUID,
        limit: int = 50,
    ) -> list[AuditLogORM]:
        """Get audit logs for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: ID of resource
            limit: Maximum results

        Returns:
            List of audit logs
        """
        result = await self.session.execute(
            select(AuditLogORM)
            .where(
                and_(
                    AuditLogORM.resource_type == resource_type,
                    AuditLogORM.resource_id == resource_id,
                )
            )
            .order_by(AuditLogORM.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self,
        admin_user_id: UUID,
        limit: int = 50,
    ) -> list[AuditLogORM]:
        """Get audit logs for a specific admin user.

        Args:
            admin_user_id: Admin user ID
            limit: Maximum results

        Returns:
            List of audit logs
        """
        result = await self.session.execute(
            select(AuditLogORM)
            .where(AuditLogORM.admin_user_id == admin_user_id)
            .order_by(AuditLogORM.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(
        self,
        limit: int = 100,
        offset: int = 0,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> tuple[list[AuditLogORM], int]:
        """Get recent audit logs with optional filters.

        Args:
            limit: Maximum results
            offset: Pagination offset
            action: Filter by action
            resource_type: Filter by resource type

        Returns:
            Tuple of (logs, total_count)
        """
        from sqlalchemy import func

        query = select(AuditLogORM)
        count_query = select(func.count()).select_from(AuditLogORM)

        if action:
            query = query.where(AuditLogORM.action == action)
            count_query = count_query.where(AuditLogORM.action == action)

        if resource_type:
            query = query.where(AuditLogORM.resource_type == resource_type)
            count_query = count_query.where(AuditLogORM.resource_type == resource_type)

        query = query.order_by(AuditLogORM.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(query)
        logs = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return logs, total

    async def get_distinct_resource_types(self) -> list[str]:
        """Get all distinct resource types from audit logs.

        Returns:
            List of unique resource types, ordered alphabetically.
        """
        from sqlalchemy import distinct

        result = await self.session.execute(
            select(distinct(AuditLogORM.resource_type))
            .where(AuditLogORM.resource_type.isnot(None))
            .order_by(AuditLogORM.resource_type)
        )
        return [row[0] for row in result.all()]

    async def get_distinct_actions(self) -> list[str]:
        """Get all distinct actions from audit logs.

        Returns:
            List of unique actions, ordered alphabetically.
        """
        from sqlalchemy import distinct

        result = await self.session.execute(
            select(distinct(AuditLogORM.action))
            .where(AuditLogORM.action.isnot(None))
            .order_by(AuditLogORM.action)
        )
        return [row[0] for row in result.all()]
