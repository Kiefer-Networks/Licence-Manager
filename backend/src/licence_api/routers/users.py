"""Users router - Employee management (HiBob employees, not admin users)."""

import base64
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.constants.paths import AVATAR_DIR
from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.domain.employee import EmployeeSource
from licence_api.models.dto.employee import (
    EmployeeBulkImport,
    EmployeeBulkImportResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
    ManagerInfo,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.csrf import CSRFProtected
from licence_api.security.rate_limit import SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.employee_service import EmployeeService
from licence_api.services.manual_employee_service import ManualEmployeeService
from licence_api.utils.validation import (
    sanitize_department,
    sanitize_search,
    sanitize_status,
    validate_sort_by,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_avatar_base64(hibob_id: str) -> str | None:
    """Load avatar from filesystem and return as base64 data URL.

    Args:
        hibob_id: HiBob employee ID

    Returns:
        Base64 data URL string or None if no avatar exists
    """
    # Validate hibob_id to prevent path traversal
    if not hibob_id or "/" in hibob_id or "\\" in hibob_id or ".." in hibob_id:
        return None

    avatar_path = AVATAR_DIR / f"{hibob_id}.jpg"

    # Ensure resolved path is within AVATAR_DIR
    try:
        resolved = avatar_path.resolve()
        if not resolved.is_relative_to(AVATAR_DIR.resolve()):
            return None
    except (ValueError, RuntimeError):
        return None

    if not avatar_path.exists():
        return None

    try:
        avatar_bytes = avatar_path.read_bytes()
        b64 = base64.b64encode(avatar_bytes).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"
    except OSError:
        return None


# Allowed status values for employees
ALLOWED_EMPLOYEE_STATUSES = {"active", "offboarded", "pending", "on_leave"}

# Allowed source values for employees
ALLOWED_EMPLOYEE_SOURCES = {"hibob", "personio", "manual"}

# Allowed sort columns for employees (whitelist to prevent injection)
ALLOWED_EMPLOYEE_SORT_COLUMNS = {
    "full_name",
    "email",
    "department",
    "status",
    "source",
    "start_date",
    "termination_date",
    "synced_at",
    "license_count",
}


def get_employee_service(db: AsyncSession = Depends(get_db)) -> EmployeeService:
    """Get EmployeeService instance."""
    return EmployeeService(db)


def get_manual_employee_service(db: AsyncSession = Depends(get_db)) -> ManualEmployeeService:
    """Get ManualEmployeeService instance."""
    return ManualEmployeeService(db)


# Employee endpoints
@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_VIEW))],
    employee_service: Annotated[EmployeeService, Depends(get_employee_service)],
    status: str | None = None,
    department: str | None = None,
    source: str | None = None,
    search: str | None = Query(default=None, max_length=200),
    sort_by: str = Query(default="full_name", max_length=50),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=50, ge=1, le=200),
) -> EmployeeListResponse:
    """List employees with optional filters."""
    # Sanitize inputs for defense in depth
    sanitized_search = sanitize_search(search)
    sanitized_department = sanitize_department(department)
    sanitized_status = sanitize_status(status, ALLOWED_EMPLOYEE_STATUSES)
    sanitized_source = sanitize_status(source, ALLOWED_EMPLOYEE_SOURCES)
    validated_sort_by = validate_sort_by(sort_by, ALLOWED_EMPLOYEE_SORT_COLUMNS, "full_name")

    offset = (page - 1) * page_size
    employees, total, license_counts, admin_account_counts = await employee_service.list_employees(
        status=sanitized_status,
        department=sanitized_department,
        source=sanitized_source,
        search=sanitized_search,
        sort_by=validated_sort_by,
        sort_dir=sort_dir,
        offset=offset,
        limit=page_size,
    )

    # Collect manager IDs and load managers in batch
    manager_ids = [emp.manager_id for emp in employees if emp.manager_id]
    managers_by_id = await employee_service.get_employees_by_ids(manager_ids) if manager_ids else {}

    items = []
    for emp in employees:
        manager_info = None
        if emp.manager_id and emp.manager_id in managers_by_id:
            mgr = managers_by_id[emp.manager_id]
            manager_info = ManagerInfo(
                id=mgr.id,
                email=mgr.email,
                full_name=mgr.full_name,
                avatar=get_avatar_base64(mgr.hibob_id),
            )

        items.append(
            EmployeeResponse(
                id=emp.id,
                hibob_id=emp.hibob_id,
                email=emp.email,
                full_name=emp.full_name,
                department=emp.department,
                status=emp.status,
                source=emp.source,
                start_date=emp.start_date,
                termination_date=emp.termination_date,
                avatar=get_avatar_base64(emp.hibob_id),
                license_count=license_counts.get(emp.id, 0),
                owned_admin_account_count=admin_account_counts.get(emp.id, 0),
                manager=manager_info,
                synced_at=emp.synced_at,
                is_manual=emp.source == EmployeeSource.MANUAL,
            )
        )

    return EmployeeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/employees/departments", response_model=list[str])
async def list_departments(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_VIEW))],
    employee_service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> list[str]:
    """Get all unique departments."""
    return await employee_service.get_departments()


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_VIEW))],
    employee_service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> EmployeeResponse:
    """Get a single employee by ID."""
    result = await employee_service.get_employee(employee_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    employee, license_count, admin_account_count = result

    # Load manager if present
    manager_info = None
    if employee.manager_id:
        managers = await employee_service.get_employees_by_ids([employee.manager_id])
        if employee.manager_id in managers:
            mgr = managers[employee.manager_id]
            manager_info = ManagerInfo(
                id=mgr.id,
                email=mgr.email,
                full_name=mgr.full_name,
                avatar=get_avatar_base64(mgr.hibob_id),
            )

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


# Manual employee management endpoints
@router.post("/employees", response_model=EmployeeResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_employee(
    request: Request,
    body: EmployeeCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_CREATE))],
    service: Annotated[ManualEmployeeService, Depends(get_manual_employee_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> EmployeeResponse:
    """Create a new manual employee. Requires employees.create permission."""
    try:
        return await service.create_employee(
            data=body,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid employee data or email already exists",
        )


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_employee(
    request: Request,
    employee_id: UUID,
    body: EmployeeUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_EDIT))],
    service: Annotated[ManualEmployeeService, Depends(get_manual_employee_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> EmployeeResponse:
    """Update a manual employee. Requires employees.edit permission.

    Only employees with source='manual' can be updated via this endpoint.
    Employees synced from HRIS (HiBob/Personio) must be updated in the source system.
    """
    try:
        return await service.update_employee(
            employee_id=employee_id,
            data=body,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid employee data or employee cannot be modified",
        )


@router.delete("/employees/{employee_id}")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_employee(
    request: Request,
    employee_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_DELETE))],
    service: Annotated[ManualEmployeeService, Depends(get_manual_employee_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> dict:
    """Delete a manual employee. Requires employees.delete permission.

    Only employees with source='manual' can be deleted.
    Employees synced from HRIS (HiBob/Personio) must be deleted in the source system.
    """
    try:
        await service.delete_employee(
            employee_id=employee_id,
            user=current_user,
            request=request,
        )
        return {"success": True, "message": "Employee deleted"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee not found or cannot be deleted",
        )


@router.post("/employees/import", response_model=EmployeeBulkImportResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def bulk_import_employees(
    request: Request,
    body: EmployeeBulkImport,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_CREATE))],
    service: Annotated[ManualEmployeeService, Depends(get_manual_employee_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> EmployeeBulkImportResponse:
    """Bulk import employees. Requires employees.create permission.

    Creates new employees or updates existing manual employees.
    Employees synced from HRIS (HiBob/Personio) will be skipped.
    Maximum 500 employees per import.
    """
    return await service.bulk_import_employees(
        employees=body.employees,
        user=current_user,
        request=request,
    )
