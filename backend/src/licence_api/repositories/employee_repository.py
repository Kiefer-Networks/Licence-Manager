"""Employee repository."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from licence_api.models.orm.employee import EmployeeORM
from licence_api.models.orm.license import LicenseORM
from licence_api.repositories.base import BaseRepository
from licence_api.utils.validation import escape_like_wildcards

# Whitelist of valid sort columns to prevent column injection
VALID_SORT_COLUMNS = {"full_name", "email", "status", "department", "start_date", "termination_date", "synced_at", "manager_email", "source", "license_count"}


class EmployeeRepository(BaseRepository[EmployeeORM]):
    """Repository for employee operations."""

    model = EmployeeORM

    async def get_by_ids(self, ids: list[UUID]) -> dict[UUID, EmployeeORM]:
        """Get multiple employees by their IDs in a single query.

        Args:
            ids: List of employee UUIDs

        Returns:
            Dict mapping employee ID to EmployeeORM
        """
        if not ids:
            return {}
        result = await self.session.execute(
            select(EmployeeORM).where(EmployeeORM.id.in_(ids))
        )
        employees = result.scalars().all()
        return {emp.id: emp for emp in employees}

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

    async def get_by_emails(self, emails: list[str]) -> dict[str, EmployeeORM]:
        """Get employees by email addresses in a single batch query.

        Args:
            emails: List of employee email addresses

        Returns:
            Dict mapping lowercase email to EmployeeORM
        """
        if not emails:
            return {}

        # Normalize emails to lowercase
        normalized_emails = [e.lower() for e in emails]

        result = await self.session.execute(
            select(EmployeeORM).where(EmployeeORM.email.in_(normalized_emails))
        )
        employees = result.scalars().all()

        # Build dict with lowercase email as key
        return {emp.email.lower(): emp for emp in employees}

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

    async def get_by_hibob_ids(self, hibob_ids: list[str]) -> dict[str, EmployeeORM]:
        """Get employees by HiBob IDs in a single batch query.

        Args:
            hibob_ids: List of HiBob employee IDs

        Returns:
            Dict mapping hibob_id to EmployeeORM
        """
        if not hibob_ids:
            return {}

        result = await self.session.execute(
            select(EmployeeORM).where(EmployeeORM.hibob_id.in_(hibob_ids))
        )
        employees = result.scalars().all()

        return {emp.hibob_id: emp for emp in employees if emp.hibob_id}

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
        source: str | None = None,
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
            source: Filter by source (hibob, personio, manual)
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

        if source:
            query = query.where(EmployeeORM.source == source)
            count_query = count_query.where(EmployeeORM.source == source)

        if search:
            # Escape LIKE wildcards to prevent pattern injection
            escaped_search = f"%{escape_like_wildcards(search)}%"
            search_filter = (
                EmployeeORM.email.ilike(escaped_search, escape="\\")
                | EmployeeORM.full_name.ilike(escaped_search, escape="\\")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Validated sorting - only allow whitelisted columns
        if sort_by not in VALID_SORT_COLUMNS:
            sort_by = "full_name"
        if sort_dir not in ("asc", "desc"):
            sort_dir = "asc"

        # Special handling for license_count sorting (computed field)
        if sort_by == "license_count":
            # Create subquery for license count
            license_count_subq = (
                select(
                    LicenseORM.employee_id,
                    func.count(LicenseORM.id).label("license_count")
                )
                .group_by(LicenseORM.employee_id)
                .subquery()
            )
            # Join with subquery and sort by count
            query = query.outerjoin(
                license_count_subq,
                EmployeeORM.id == license_count_subq.c.employee_id
            )
            sort_column = func.coalesce(license_count_subq.c.license_count, 0)
        else:
            sort_column = getattr(EmployeeORM, sort_by, EmployeeORM.full_name)

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
        manager_email: str | None = None,
    ) -> EmployeeORM:
        """Create or update employee by HiBob ID.

        Args:
            hibob_id: HiBob employee ID (or Personio employee ID)
            email: Employee email
            full_name: Full name
            department: Department name
            status: Employment status
            start_date: Start date
            termination_date: Termination date
            synced_at: Sync timestamp
            manager_email: Manager's email address (resolved to ID after sync)

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
            existing.manager_email = manager_email
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
            manager_email=manager_email,
        )

    async def resolve_manager_ids(self) -> int:
        """Resolve manager_email to manager_id for all employees.

        This should be called after syncing all employees to link
        managers by their email addresses.

        Uses batch query to avoid N+1 problem when resolving managers.

        Returns:
            Number of manager relationships resolved
        """
        # Get all employees with manager_email
        query = select(EmployeeORM).where(
            EmployeeORM.manager_email.isnot(None)
        )
        result = await self.session.execute(query)
        employees = result.scalars().all()

        if not employees:
            return 0

        # Collect all unique manager emails
        manager_emails = list({
            emp.manager_email.lower()
            for emp in employees
            if emp.manager_email
        })

        # Batch fetch all potential managers in a single query
        managers_by_email = await self.get_by_emails(manager_emails)

        # Resolve manager_id for each employee
        resolved = 0
        for emp in employees:
            if emp.manager_email:
                manager = managers_by_email.get(emp.manager_email.lower())
                if manager and manager.id != emp.id:  # Avoid self-reference
                    emp.manager_id = manager.id
                    resolved += 1

        await self.session.flush()
        return resolved

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

    async def email_exists(self, email: str, exclude_id: UUID | None = None) -> bool:
        """Check if an email already exists.

        Args:
            email: Email to check
            exclude_id: Optionally exclude an employee ID from the check

        Returns:
            True if email exists, False otherwise
        """
        query = select(func.count()).select_from(EmployeeORM).where(
            func.lower(EmployeeORM.email) == email.lower()
        )
        if exclude_id:
            query = query.where(EmployeeORM.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar_one() > 0

    async def is_manual_employee(self, employee_id: UUID) -> bool:
        """Check if an employee is a manual employee.

        Args:
            employee_id: Employee UUID

        Returns:
            True if employee source is 'manual', False otherwise
        """
        result = await self.session.execute(
            select(EmployeeORM.source).where(EmployeeORM.id == employee_id)
        )
        source = result.scalar_one_or_none()
        return source == "manual"

    async def count_by_source(self) -> dict[str, int]:
        """Count employees by source.

        Returns:
            Dict mapping source to count
        """
        query = select(EmployeeORM.source, func.count()).group_by(EmployeeORM.source)
        result = await self.session.execute(query)
        return dict(result.all())
