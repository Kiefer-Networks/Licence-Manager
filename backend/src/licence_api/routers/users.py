"""Users router - Employee management (HiBob employees, not admin users)."""

import base64
import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.employee import EmployeeResponse, EmployeeListResponse
from licence_api.security.auth import require_permission, Permissions
from licence_api.services.employee_service import EmployeeService
from licence_api.utils.validation import sanitize_department, sanitize_search, sanitize_status

logger = logging.getLogger(__name__)
router = APIRouter()

# Avatar storage directory (same as sync_service.py)
AVATAR_DIR = Path(__file__).parent.parent.parent.parent / "data" / "avatars"


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
    except (OSError, IOError):
        return None


# Allowed status values for employees
ALLOWED_EMPLOYEE_STATUSES = {"active", "offboarded", "pending", "on_leave"}


def get_employee_service(db: AsyncSession = Depends(get_db)) -> EmployeeService:
    """Get EmployeeService instance."""
    return EmployeeService(db)


# Employee endpoints
@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_VIEW))],
    employee_service: Annotated[EmployeeService, Depends(get_employee_service)],
    status: str | None = None,
    department: str | None = None,
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

    offset = (page - 1) * page_size
    employees, total, license_counts = await employee_service.list_employees(
        status=sanitized_status,
        department=sanitized_department,
        search=sanitized_search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        offset=offset,
        limit=page_size,
    )

    items = []
    for emp in employees:
        items.append(
            EmployeeResponse(
                id=emp.id,
                hibob_id=emp.hibob_id,
                email=emp.email,
                full_name=emp.full_name,
                department=emp.department,
                status=emp.status,
                start_date=emp.start_date,
                termination_date=emp.termination_date,
                avatar=get_avatar_base64(emp.hibob_id),
                license_count=license_counts.get(emp.id, 0),
                synced_at=emp.synced_at,
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

    employee, license_count = result

    return EmployeeResponse(
        id=employee.id,
        hibob_id=employee.hibob_id,
        email=employee.email,
        full_name=employee.full_name,
        department=employee.department,
        status=employee.status,
        start_date=employee.start_date,
        termination_date=employee.termination_date,
        avatar=get_avatar_base64(employee.hibob_id),
        license_count=license_count,
        synced_at=employee.synced_at,
    )
