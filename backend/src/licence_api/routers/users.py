"""Users router."""

import base64
import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser, UserRole
from licence_api.models.dto.employee import EmployeeResponse, EmployeeListResponse
from licence_api.security.auth import get_current_user, require_admin
from licence_api.services.user_service import UserService
from licence_api.repositories.employee_repository import EmployeeRepository

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
    except Exception:
        return None


class AdminUserResponse(BaseModel):
    """Admin user response."""

    id: UUID
    email: str
    name: str | None
    picture_url: str | None
    role: UserRole

    class Config:
        from_attributes = True


class UpdateUserRoleRequest(BaseModel):
    """Request to update user role."""

    role: UserRole


# Admin users endpoints
@router.get("/admins", response_model=list[AdminUserResponse])
async def list_admin_users(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminUserResponse]:
    """List all admin users."""
    service = UserService(db)
    users = await service.list_users()
    return [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            picture_url=u.picture_url,
            role=u.role,
        )
        for u in users
    ]


@router.put("/admins/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: UUID,
    request: UpdateUserRoleRequest,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUserResponse:
    """Update an admin user's role. Admin only."""
    service = UserService(db)
    user = await service.update_user_role(user_id, request.role)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        role=user.role,
    )


# Employee endpoints
@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
    department: str | None = None,
    search: str | None = Query(default=None, max_length=200),
    sort_by: str = "full_name",
    sort_dir: str = "asc",
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=50, ge=1, le=200),
) -> EmployeeListResponse:
    """List employees with optional filters."""
    repo = EmployeeRepository(db)
    offset = (page - 1) * page_size
    employees, total = await repo.get_all_with_filters(
        status=status,
        department=department,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        offset=offset,
        limit=page_size,
    )

    # Get license counts in a single batch query (avoids N+1)
    from licence_api.repositories.license_repository import LicenseRepository
    license_repo = LicenseRepository(db)
    employee_ids = [emp.id for emp in employees]
    license_counts = await license_repo.count_by_employee_ids(employee_ids)

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
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[str]:
    """Get all unique departments."""
    repo = EmployeeRepository(db)
    return await repo.get_all_departments()


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeResponse:
    """Get a single employee by ID."""
    repo = EmployeeRepository(db)
    employee = await repo.get_by_id(employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    # Get license count in batch query (consistent with list endpoint)
    from licence_api.repositories.license_repository import LicenseRepository
    license_repo = LicenseRepository(db)
    license_counts = await license_repo.count_by_employee_ids([employee_id])

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
        license_count=license_counts.get(employee_id, 0),
        synced_at=employee.synced_at,
    )
