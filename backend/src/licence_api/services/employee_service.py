"""Employee service for managing HiBob employees."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository


class EmployeeService:
    """Service for employee operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.employee_repo = EmployeeRepository(session)
        self.license_repo = LicenseRepository(session)

    async def list_employees(
        self,
        status: str | None = None,
        department: str | None = None,
        search: str | None = None,
        sort_by: str = "full_name",
        sort_dir: str = "asc",
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list, int, dict[UUID, int], dict[UUID, int]]:
        """List employees with filters.

        Args:
            status: Filter by status
            department: Filter by department
            search: Search query
            sort_by: Sort field
            sort_dir: Sort direction
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (employees, total, license_counts, admin_account_counts)
        """
        employees, total = await self.employee_repo.get_all_with_filters(
            status=status,
            department=department,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=offset,
            limit=limit,
        )

        # Get license counts in a single batch query (avoids N+1)
        employee_ids = [emp.id for emp in employees]
        license_counts = await self.license_repo.count_by_employee_ids(employee_ids)
        admin_account_counts = await self.license_repo.count_admin_accounts_by_owner_ids(employee_ids)

        return employees, total, license_counts, admin_account_counts

    async def get_departments(self) -> list[str]:
        """Get all unique departments.

        Returns:
            List of department names
        """
        return await self.employee_repo.get_all_departments()

    async def get_employee(self, employee_id: UUID) -> tuple | None:
        """Get employee by ID with license count and admin account count.

        Args:
            employee_id: Employee UUID

        Returns:
            Tuple of (employee, license_count, admin_account_count) or None if not found
        """
        employee = await self.employee_repo.get_by_id(employee_id)
        if employee is None:
            return None

        license_counts = await self.license_repo.count_by_employee_ids([employee_id])
        license_count = license_counts.get(employee_id, 0)

        admin_account_counts = await self.license_repo.count_admin_accounts_by_owner_ids([employee_id])
        admin_account_count = admin_account_counts.get(employee_id, 0)

        return employee, license_count, admin_account_count

    async def get_employees_by_ids(self, employee_ids: list[UUID]) -> dict:
        """Get multiple employees by IDs.

        Args:
            employee_ids: List of employee UUIDs

        Returns:
            Dict mapping employee ID to EmployeeORM
        """
        return await self.employee_repo.get_by_ids(employee_ids)
