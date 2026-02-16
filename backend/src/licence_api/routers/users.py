"""Users router - Employee management (HiBob employees, not admin users)."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from licence_api.dependencies import get_employee_service, get_manual_employee_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.employee import (
    EmployeeBulkImport,
    EmployeeBulkImportResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import (
    API_DEFAULT_LIMIT,
    EXPENSIVE_READ_LIMIT,
    SENSITIVE_OPERATION_LIMIT,
    limiter,
)
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


# Employee endpoints
@router.get("/employees", response_model=EmployeeListResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_employees(
    request: Request,
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

    return await employee_service.list_employees_response(
        status=sanitized_status,
        department=sanitized_department,
        source=sanitized_source,
        search=sanitized_search,
        sort_by=validated_sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.get("/employees/departments", response_model=list[str])
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_departments(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_VIEW))],
    employee_service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> list[str]:
    """Get all unique departments."""
    return await employee_service.get_departments()


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_employee(
    request: Request,
    employee_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_VIEW))],
    employee_service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> EmployeeResponse:
    """Get a single employee by ID."""
    response = await employee_service.get_employee_response(employee_id)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return response


# Manual employee management endpoints
@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_employee(
    request: Request,
    body: EmployeeCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_CREATE))],
    service: Annotated[ManualEmployeeService, Depends(get_manual_employee_service)],
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


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_employee(
    request: Request,
    employee_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_DELETE))],
    service: Annotated[ManualEmployeeService, Depends(get_manual_employee_service)],
) -> None:
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
        return None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee not found or cannot be deleted",
        )


@router.post("/employees/import", response_model=EmployeeBulkImportResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def bulk_import_employees(
    request: Request,
    body: EmployeeBulkImport,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_CREATE))],
    service: Annotated[ManualEmployeeService, Depends(get_manual_employee_service)],
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
