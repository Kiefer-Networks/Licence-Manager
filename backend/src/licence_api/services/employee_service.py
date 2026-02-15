"""Employee service for managing HiBob employees."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.employee import EmployeeSource
from licence_api.models.dto.employee import (
    EmployeeListResponse,
    EmployeeResponse,
    ManagerInfo,
)
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.services.auth_service import get_avatar_base64


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
        source: str | None = None,
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
            source: Filter by source (hibob, personio, manual)
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
            source=source,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=offset,
            limit=limit,
        )

        # Get license counts in a single batch query (avoids N+1)
        employee_ids = [emp.id for emp in employees]
        license_counts = await self.license_repo.count_by_employee_ids(employee_ids)
        admin_account_counts = await self.license_repo.count_admin_accounts_by_owner_ids(
            employee_ids
        )

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

        admin_account_counts = await self.license_repo.count_admin_accounts_by_owner_ids(
            [employee_id]
        )
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

    def _build_manager_info(self, manager) -> ManagerInfo:
        """Build ManagerInfo DTO from a manager ORM object.

        Args:
            manager: Manager ORM object

        Returns:
            ManagerInfo DTO
        """
        return ManagerInfo(
            id=manager.id,
            email=manager.email,
            full_name=manager.full_name,
            avatar=get_avatar_base64(manager.hibob_id),
        )

    def _build_employee_response(
        self,
        employee,
        license_count: int,
        admin_account_count: int,
        manager_info: ManagerInfo | None,
    ) -> EmployeeResponse:
        """Build EmployeeResponse DTO from an employee ORM object.

        Args:
            employee: Employee ORM object
            license_count: Number of licenses for this employee
            admin_account_count: Number of admin accounts owned by this employee
            manager_info: Optional ManagerInfo DTO

        Returns:
            EmployeeResponse DTO
        """
        return EmployeeResponse(
            id=employee.id,
            hibob_id=employee.hibob_id,
            email=employee.email,
            full_name=employee.full_name,
            department=employee.department,
            status=employee.status,
            source=employee.source,
            start_date=employee.start_date,
            termination_date=employee.termination_date,
            avatar=get_avatar_base64(employee.hibob_id),
            license_count=license_count,
            owned_admin_account_count=admin_account_count,
            manager=manager_info,
            synced_at=employee.synced_at,
            is_manual=employee.source == EmployeeSource.MANUAL,
        )

    async def list_employees_response(
        self,
        status: str | None = None,
        department: str | None = None,
        source: str | None = None,
        search: str | None = None,
        sort_by: str = "full_name",
        sort_dir: str = "asc",
        page: int = 1,
        page_size: int = 50,
    ) -> EmployeeListResponse:
        """List employees and return ready-to-use response DTOs.

        Args:
            status: Filter by status
            department: Filter by department
            source: Filter by source (hibob, personio, manual)
            search: Search query
            sort_by: Sort field
            sort_dir: Sort direction
            page: Page number (1-indexed)
            page_size: Page size

        Returns:
            EmployeeListResponse with fully assembled DTOs
        """
        offset = (page - 1) * page_size
        employees, total, license_counts, admin_account_counts = await self.list_employees(
            status=status,
            department=department,
            source=source,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=offset,
            limit=page_size,
        )

        # Collect manager IDs and load managers in batch
        manager_ids = [emp.manager_id for emp in employees if emp.manager_id]
        managers_by_id = await self.get_employees_by_ids(manager_ids) if manager_ids else {}

        items = []
        for emp in employees:
            manager_info = None
            if emp.manager_id and emp.manager_id in managers_by_id:
                manager_info = self._build_manager_info(managers_by_id[emp.manager_id])

            items.append(
                self._build_employee_response(
                    employee=emp,
                    license_count=license_counts.get(emp.id, 0),
                    admin_account_count=admin_account_counts.get(emp.id, 0),
                    manager_info=manager_info,
                )
            )

        return EmployeeListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_employee_response(self, employee_id: UUID) -> EmployeeResponse | None:
        """Get employee by ID and return a ready-to-use response DTO.

        Args:
            employee_id: Employee UUID

        Returns:
            EmployeeResponse DTO or None if not found
        """
        result = await self.get_employee(employee_id)
        if result is None:
            return None

        employee, license_count, admin_account_count = result

        # Load manager if present
        manager_info = None
        if employee.manager_id:
            managers = await self.get_employees_by_ids([employee.manager_id])
            if employee.manager_id in managers:
                manager_info = self._build_manager_info(managers[employee.manager_id])

        return self._build_employee_response(
            employee=employee,
            license_count=license_count,
            admin_account_count=admin_account_count,
            manager_info=manager_info,
        )
