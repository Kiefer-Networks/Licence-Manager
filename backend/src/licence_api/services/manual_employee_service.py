"""Manual employee service for managing employees without HRIS."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.domain.employee import EmployeeSource
from licence_api.models.dto.employee import (
    EmployeeBulkImportItem,
    EmployeeBulkImportResponse,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    ManagerInfo,
)
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType


class ManualEmployeeService:
    """Service for managing manual employees."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.employee_repo = EmployeeRepository(session)
        self.audit_service = AuditService(session)

    async def _build_employee_response(
        self,
        employee_orm,
        license_count: int = 0,
        admin_account_count: int = 0,
        manager_info: ManagerInfo | None = None,
        avatar: str | None = None,
    ) -> EmployeeResponse:
        """Build an EmployeeResponse from ORM object."""
        return EmployeeResponse(
            id=employee_orm.id,
            hibob_id=employee_orm.hibob_id,
            email=employee_orm.email,
            full_name=employee_orm.full_name,
            department=employee_orm.department,
            status=employee_orm.status,
            source=employee_orm.source,
            start_date=employee_orm.start_date,
            termination_date=employee_orm.termination_date,
            avatar=avatar,
            license_count=license_count,
            owned_admin_account_count=admin_account_count,
            manager=manager_info,
            synced_at=employee_orm.synced_at,
            is_manual=employee_orm.source == EmployeeSource.MANUAL,
        )

    async def create_employee(
        self,
        data: EmployeeCreate,
        user: AdminUser,
        request: Request | None = None,
    ) -> EmployeeResponse:
        """Create a manual employee.

        Args:
            data: Employee creation data
            user: Admin user creating the employee
            request: HTTP request for audit logging

        Returns:
            Created EmployeeResponse

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        if await self.employee_repo.email_exists(data.email):
            raise ValueError("An employee with this email already exists")

        now = datetime.now(timezone.utc)

        # Generate a unique hibob_id for manual employees
        manual_id = f"manual-{uuid4().hex[:12]}"

        employee_orm = await self.employee_repo.create(
            hibob_id=manual_id,
            email=data.email.lower(),
            full_name=data.full_name,
            department=data.department,
            status=data.status,
            start_date=data.start_date,
            termination_date=data.termination_date,
            manager_email=data.manager_email.lower() if data.manager_email else None,
            source=EmployeeSource.MANUAL,
            synced_at=now,
        )

        # Resolve manager if provided
        if data.manager_email:
            await self.employee_repo.resolve_manager_ids()
            employee_orm = await self.employee_repo.refresh(employee_orm)

        # Audit log
        await self.audit_service.log(
            action=AuditAction.EMPLOYEE_CREATE,
            resource_type=ResourceType.EMPLOYEE,
            resource_id=employee_orm.id,
            user=user,
            request=request,
            details={
                "email": data.email,
                "full_name": data.full_name,
                "department": data.department,
                "source": EmployeeSource.MANUAL,
            },
        )

        # Note: Commit handled by get_db() dependency after endpoint completes
        return await self._build_employee_response(employee_orm)

    async def update_employee(
        self,
        employee_id: UUID,
        data: EmployeeUpdate,
        user: AdminUser,
        request: Request | None = None,
    ) -> EmployeeResponse:
        """Update a manual employee.

        Args:
            employee_id: Employee UUID
            data: Employee update data
            user: Admin user making the update
            request: HTTP request for audit logging

        Returns:
            Updated EmployeeResponse

        Raises:
            ValueError: If employee not found, not manual, or email already exists
        """
        employee_orm = await self.employee_repo.get_by_id(employee_id)
        if not employee_orm:
            raise ValueError("Employee not found")

        if employee_orm.source != EmployeeSource.MANUAL:
            raise ValueError("Only manual employees can be edited")

        # Build update dict
        update_data = {}
        changes = {}

        if data.email is not None:
            new_email = data.email.lower()
            if new_email != employee_orm.email.lower():
                if await self.employee_repo.email_exists(new_email, exclude_id=employee_id):
                    raise ValueError("An employee with this email already exists")
                update_data["email"] = new_email
                changes["email"] = {"old": employee_orm.email, "new": new_email}

        if data.full_name is not None and data.full_name != employee_orm.full_name:
            update_data["full_name"] = data.full_name
            changes["full_name"] = {"old": employee_orm.full_name, "new": data.full_name}

        if data.department is not None and data.department != employee_orm.department:
            update_data["department"] = data.department
            changes["department"] = {"old": employee_orm.department, "new": data.department}

        if data.status is not None and data.status != employee_orm.status:
            update_data["status"] = data.status
            changes["status"] = {"old": employee_orm.status, "new": data.status}

        if data.start_date is not None and data.start_date != employee_orm.start_date:
            update_data["start_date"] = data.start_date
            changes["start_date"] = {
                "old": str(employee_orm.start_date) if employee_orm.start_date else None,
                "new": str(data.start_date),
            }

        if data.termination_date is not None:
            if data.termination_date != employee_orm.termination_date:
                update_data["termination_date"] = data.termination_date
                changes["termination_date"] = {
                    "old": str(employee_orm.termination_date) if employee_orm.termination_date else None,
                    "new": str(data.termination_date),
                }

        if data.manager_email is not None:
            manager_email = data.manager_email.lower() if data.manager_email else None
            if manager_email != employee_orm.manager_email:
                update_data["manager_email"] = manager_email
                update_data["manager_id"] = None  # Will be re-resolved
                changes["manager_email"] = {"old": employee_orm.manager_email, "new": manager_email}

        if update_data:
            update_data["synced_at"] = datetime.now(timezone.utc)
            employee_orm = await self.employee_repo.update(employee_id, **update_data)

            # Resolve manager if changed
            if "manager_email" in update_data:
                await self.employee_repo.resolve_manager_ids()
                employee_orm = await self.employee_repo.refresh(employee_orm)

        # Audit log
        await self.audit_service.log(
            action=AuditAction.EMPLOYEE_UPDATE,
            resource_type=ResourceType.EMPLOYEE,
            resource_id=employee_id,
            user=user,
            request=request,
            details={"changes": changes} if changes else {"no_changes": True},
        )

        # Note: Commit handled by get_db() dependency after endpoint completes
        return await self._build_employee_response(employee_orm)

    async def delete_employee(
        self,
        employee_id: UUID,
        user: AdminUser,
        request: Request | None = None,
    ) -> None:
        """Delete a manual employee.

        Args:
            employee_id: Employee UUID
            user: Admin user deleting the employee
            request: HTTP request for audit logging

        Raises:
            ValueError: If employee not found or not manual
        """
        employee_orm = await self.employee_repo.get_by_id(employee_id)
        if not employee_orm:
            raise ValueError("Employee not found")

        if employee_orm.source != EmployeeSource.MANUAL:
            raise ValueError("Only manual employees can be deleted")

        # Store info for audit log before deletion
        employee_email = employee_orm.email
        employee_name = employee_orm.full_name

        await self.employee_repo.delete(employee_id)

        # Audit log
        await self.audit_service.log(
            action=AuditAction.EMPLOYEE_DELETE,
            resource_type=ResourceType.EMPLOYEE,
            resource_id=employee_id,
            user=user,
            request=request,
            details={
                "email": employee_email,
                "full_name": employee_name,
                "source": EmployeeSource.MANUAL,
            },
        )

        # Note: Commit handled by get_db() dependency after endpoint completes

    async def bulk_import_employees(
        self,
        employees: list[EmployeeBulkImportItem],
        user: AdminUser,
        request: Request | None = None,
    ) -> EmployeeBulkImportResponse:
        """Bulk import employees.

        Creates new employees or updates existing ones if email matches.
        Only updates manual employees; synced employees are skipped.

        Args:
            employees: List of employees to import
            user: Admin user performing the import
            request: HTTP request for audit logging

        Returns:
            EmployeeBulkImportResponse with counts
        """
        created = 0
        updated = 0
        skipped = 0
        errors: list[str] = []
        now = datetime.now(timezone.utc)

        for item in employees:
            try:
                email_lower = item.email.lower()
                existing = await self.employee_repo.get_by_email(email_lower)

                if existing:
                    # Only update manual employees
                    if existing.source != EmployeeSource.MANUAL:
                        skipped += 1
                        errors.append(f"Skipped {email_lower}: employee is synced from HRIS")
                        continue

                    # Update existing manual employee
                    await self.employee_repo.update(
                        existing.id,
                        full_name=item.full_name,
                        department=item.department,
                        status=item.status,
                        start_date=item.start_date,
                        manager_email=item.manager_email.lower() if item.manager_email else None,
                        synced_at=now,
                    )
                    updated += 1
                else:
                    # Create new manual employee
                    manual_id = f"manual-{uuid4().hex[:12]}"
                    await self.employee_repo.create(
                        hibob_id=manual_id,
                        email=email_lower,
                        full_name=item.full_name,
                        department=item.department,
                        status=item.status,
                        start_date=item.start_date,
                        manager_email=item.manager_email.lower() if item.manager_email else None,
                        source=EmployeeSource.MANUAL,
                        synced_at=now,
                    )
                    created += 1

            except Exception:
                skipped += 1
                # Sanitize error message - don't expose internal details
                errors.append(f"Failed to process employee: {item.email}")

        # Resolve manager IDs for all newly created/updated employees
        await self.employee_repo.resolve_manager_ids()

        # Audit log
        await self.audit_service.log(
            action=AuditAction.EMPLOYEE_BULK_IMPORT,
            resource_type=ResourceType.EMPLOYEE,
            resource_id=None,
            user=user,
            request=request,
            details={
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "total": len(employees),
            },
        )

        # Note: Commit handled by get_db() dependency after endpoint completes

        return EmployeeBulkImportResponse(
            created=created,
            updated=updated,
            skipped=skipped,
            errors=errors,
        )
