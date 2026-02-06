"""Audit log repository."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import String, and_, cast, distinct, func, or_, select

from licence_api.models.orm.admin_user import AdminUserORM
from licence_api.models.orm.audit_log import AuditLogORM
from licence_api.repositories.base import BaseRepository
from licence_api.utils.validation import escape_like_wildcards


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
        admin_user_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> tuple[list[AuditLogORM], int]:
        """Get recent audit logs with optional filters.

        Args:
            limit: Maximum results
            offset: Pagination offset
            action: Filter by action
            resource_type: Filter by resource type
            admin_user_id: Filter by admin user ID
            date_from: Filter by minimum date
            date_to: Filter by maximum date
            search: Full-text search over email, resource_id, and changes

        Returns:
            Tuple of (logs, total_count)
        """
        # Base query with join to admin_users for search
        query = select(AuditLogORM)
        count_query = select(func.count()).select_from(AuditLogORM)

        # For search, we need to join with admin_users
        if search:
            query = query.outerjoin(AdminUserORM, AuditLogORM.admin_user_id == AdminUserORM.id)
            count_query = count_query.outerjoin(
                AdminUserORM, AuditLogORM.admin_user_id == AdminUserORM.id
            )

        conditions = []

        if action:
            conditions.append(AuditLogORM.action == action)

        if resource_type:
            conditions.append(AuditLogORM.resource_type == resource_type)

        if admin_user_id:
            conditions.append(AuditLogORM.admin_user_id == admin_user_id)

        if date_from:
            conditions.append(AuditLogORM.created_at >= date_from)

        if date_to:
            conditions.append(AuditLogORM.created_at <= date_to)

        if search:
            # Escape SQL wildcards to prevent LIKE injection
            escaped_search = escape_like_wildcards(search.lower())
            search_term = f"%{escaped_search}%"
            search_conditions = [
                func.lower(AdminUserORM.email).like(search_term, escape="\\"),
                cast(AuditLogORM.resource_id, String).like(search_term, escape="\\"),
                cast(AuditLogORM.changes, String).ilike(search_term, escape="\\"),
                func.lower(AuditLogORM.action).like(search_term, escape="\\"),
                func.lower(AuditLogORM.resource_type).like(search_term, escape="\\"),
            ]
            conditions.append(or_(*search_conditions))

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

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
        result = await self.session.execute(
            select(distinct(AuditLogORM.action))
            .where(AuditLogORM.action.isnot(None))
            .order_by(AuditLogORM.action)
        )
        return [row[0] for row in result.all()]

    async def get_distinct_users(self) -> list[tuple[UUID, str]]:
        """Get all distinct admin users who have audit log entries.

        Returns:
            List of tuples (user_id, email) for users with audit entries.
        """
        result = await self.session.execute(
            select(distinct(AuditLogORM.admin_user_id), AdminUserORM.email)
            .join(AdminUserORM, AuditLogORM.admin_user_id == AdminUserORM.id)
            .where(AuditLogORM.admin_user_id.isnot(None))
            .order_by(AdminUserORM.email)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def get_all(
        self,
        action: str | None = None,
        resource_type: str | None = None,
        admin_user_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> list[AuditLogORM]:
        """Get all audit logs matching filters (for export).

        Args:
            action: Filter by action
            resource_type: Filter by resource type
            admin_user_id: Filter by admin user ID
            date_from: Filter by minimum date
            date_to: Filter by maximum date
            search: Full-text search

        Returns:
            List of all matching audit logs
        """
        query = select(AuditLogORM)

        if search:
            query = query.outerjoin(AdminUserORM, AuditLogORM.admin_user_id == AdminUserORM.id)

        conditions = []

        if action:
            conditions.append(AuditLogORM.action == action)

        if resource_type:
            conditions.append(AuditLogORM.resource_type == resource_type)

        if admin_user_id:
            conditions.append(AuditLogORM.admin_user_id == admin_user_id)

        if date_from:
            conditions.append(AuditLogORM.created_at >= date_from)

        if date_to:
            conditions.append(AuditLogORM.created_at <= date_to)

        if search:
            # Escape SQL wildcards to prevent LIKE injection
            escaped_search = escape_like_wildcards(search.lower())
            search_term = f"%{escaped_search}%"
            search_conditions = [
                func.lower(AdminUserORM.email).like(search_term, escape="\\"),
                cast(AuditLogORM.resource_id, String).like(search_term, escape="\\"),
                cast(AuditLogORM.changes, String).ilike(search_term, escape="\\"),
                func.lower(AuditLogORM.action).like(search_term, escape="\\"),
                func.lower(AuditLogORM.resource_type).like(search_term, escape="\\"),
            ]
            conditions.append(or_(*search_conditions))

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AuditLogORM.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())
