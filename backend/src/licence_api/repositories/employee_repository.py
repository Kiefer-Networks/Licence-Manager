"""Employee repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.employee import EmployeeORM
from licence_api.repositories.base import BaseRepository

# Whitelist of valid sort columns to prevent column injection
VALID_SORT_COLUMNS = {"full_name", "email", "status", "department", "start_date", "termination_date", "synced_at"}


class EmployeeRepository(BaseRepository[EmployeeORM]):
    """Repository for employee operations."""

    model = EmployeeORM

    async def get_by_email(self, email: str) -> EmployeeORM | None:
        """Get employee by email.

        Args:
            email: Employee email address

        Returns:
            EmployeeORM or None if not found
        """
        result = await self.session.execute(
            select(EmployeeORM).where(EmployeeORM.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_hibob_id(self, hibob_id: str) -> EmployeeORM | None:
        """Get employee by HiBob ID.

        Args:
            hibob_id: HiBob employee ID

        Returns:
            EmployeeORM or None if not found
        """
        result = await self.session.execute(
            select(EmployeeORM).where(EmployeeORM.hibob_id == hibob_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[EmployeeORM]:
        """Get all employees.

        Returns:
            List of all employees
        """
        result = await self.session.execute(select(EmployeeORM))
        return list(result.scalars().all())

    async def get_all_with_filters(
        self,
        status: str | None = None,
        department: str | None = None,
        search: str | None = None,
        sort_by: str = "full_name",
        sort_dir: str = "asc",
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[EmployeeORM], int]:
        """Get employees with optional filters.

        Args:
            status: Filter by status
            department: Filter by department
            search: Search in name or email
            sort_by: Column to sort by
            sort_dir: Sort direction (asc or desc)
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (employees, total_count)
        """
        query = select(EmployeeORM)
        count_query = select(func.count()).select_from(EmployeeORM)

        if status:
            query = query.where(EmployeeORM.status == status)
            count_query = count_query.where(EmployeeORM.status == status)

        if department:
            query = query.where(EmployeeORM.department == department)
            count_query = count_query.where(EmployeeORM.department == department)

        if search:
            search_filter = (
                EmployeeORM.email.ilike(f"%{search}%")
                | EmployeeORM.full_name.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Validated sorting - only allow whitelisted columns
        if sort_by not in VALID_SORT_COLUMNS:
            sort_by = "full_name"
        sort_column = getattr(EmployeeORM, sort_by, EmployeeORM.full_name)
        if sort_dir not in ("asc", "desc"):
            sort_dir = "asc"
        if sort_dir == "desc":
            query = query.order_by(sort_column.desc().nulls_last())
        else:
            query = query.order_by(sort_column.asc().nulls_last())

        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        employees = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return employees, total

    async def get_recently_offboarded(
        self,
        days: int = 30,
        department: str | None = None,
        limit: int = 10,
    ) -> list[EmployeeORM]:
        """Get recently offboarded employees.

        Args:
            days: Number of days to look back
            department: Optional department filter
            limit: Maximum number of results

        Returns:
            List of recently offboarded employees
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        query = (
            select(EmployeeORM)
            .where(EmployeeORM.status == "offboarded")
            .where(EmployeeORM.termination_date >= cutoff.date())
        )

        if department:
            query = query.where(EmployeeORM.department == department)

        query = query.order_by(EmployeeORM.termination_date.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def upsert(
        self,
        hibob_id: str,
        email: str,
        full_name: str,
        department: str | None,
        status: str,
        start_date: datetime | None,
        termination_date: datetime | None,
        synced_at: datetime,
    ) -> EmployeeORM:
        """Create or update employee by HiBob ID.

        Args:
            hibob_id: HiBob employee ID
            email: Employee email
            full_name: Full name
            department: Department name
            status: Employment status
            start_date: Start date
            termination_date: Termination date
            synced_at: Sync timestamp

        Returns:
            Created or updated EmployeeORM
        """
        existing = await self.get_by_hibob_id(hibob_id)

        if existing:
            existing.email = email
            existing.full_name = full_name
            existing.department = department
            existing.status = status
            existing.start_date = start_date
            existing.termination_date = termination_date
            existing.synced_at = synced_at
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        return await self.create(
            hibob_id=hibob_id,
            email=email,
            full_name=full_name,
            department=department,
            status=status,
            start_date=start_date,
            termination_date=termination_date,
            synced_at=synced_at,
        )

    async def count_by_status(self, department: str | None = None) -> dict[str, int]:
        """Count employees by status.

        Args:
            department: Optional department filter

        Returns:
            Dict mapping status to count
        """
        query = select(EmployeeORM.status, func.count()).group_by(EmployeeORM.status)
        if department:
            query = query.where(EmployeeORM.department == department)
        result = await self.session.execute(query)
        return dict(result.all())

    async def get_all_departments(self) -> list[str]:
        """Get all unique departments.

        Returns:
            Sorted list of department names
        """
        result = await self.session.execute(
            select(EmployeeORM.department)
            .where(EmployeeORM.department.isnot(None))
            .distinct()
            .order_by(EmployeeORM.department)
        )
        return [r[0] for r in result.all()]
