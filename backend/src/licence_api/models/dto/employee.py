"""Employee DTOs."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from licence_api.models.domain.employee import EmployeeSource, EmployeeStatus


class ManagerInfo(BaseModel):
    """Manager info for employee response."""

    id: UUID
    email: EmailStr
    full_name: str
    avatar: str | None = None  # Base64 data URL or None if no avatar

    class Config:
        """Pydantic config."""

        from_attributes = True


class EmployeeResponse(BaseModel):
    """Employee response DTO."""

    id: UUID
    hibob_id: str
    email: EmailStr
    full_name: str
    department: str | None = None
    status: EmployeeStatus
    source: EmployeeSource = EmployeeSource.HIBOB
    start_date: date | None = None
    termination_date: date | None = None
    avatar: str | None = None  # Base64 data URL or None if no avatar
    license_count: int = 0
    owned_admin_account_count: int = 0  # Number of admin accounts owned by this employee
    manager: ManagerInfo | None = None
    synced_at: datetime
    is_manual: bool = False  # Convenience field: True if source == manual

    class Config:
        """Pydantic config."""

        from_attributes = True


class EmployeeListResponse(BaseModel):
    """Employee list response DTO."""

    items: list[EmployeeResponse]
    total: int
    page: int
    page_size: int


class EmployeeCreate(BaseModel):
    """DTO for creating a manual employee."""

    email: EmailStr = Field(description="Employee email address")
    full_name: str = Field(min_length=1, max_length=255, description="Full name of the employee")
    department: str | None = Field(default=None, max_length=255, description="Department name")
    status: EmployeeStatus = Field(default=EmployeeStatus.ACTIVE, description="Employment status")
    start_date: date | None = Field(default=None, description="Employment start date")
    termination_date: date | None = Field(default=None, description="Employment termination date")
    manager_email: EmailStr | None = Field(default=None, description="Manager's email address")


class EmployeeUpdate(BaseModel):
    """DTO for updating a manual employee."""

    email: EmailStr | None = Field(default=None, description="Employee email address")
    full_name: str | None = Field(default=None, min_length=1, max_length=255, description="Full name of the employee")
    department: str | None = Field(default=None, max_length=255, description="Department name")
    status: EmployeeStatus | None = Field(default=None, description="Employment status")
    start_date: date | None = Field(default=None, description="Employment start date")
    termination_date: date | None = Field(default=None, description="Employment termination date")
    manager_email: EmailStr | None = Field(default=None, description="Manager's email address")


class EmployeeBulkImportItem(BaseModel):
    """Single employee item for bulk import."""

    email: EmailStr = Field(description="Employee email address")
    full_name: str = Field(min_length=1, max_length=255, description="Full name of the employee")
    department: str | None = Field(default=None, max_length=255, description="Department name")
    status: EmployeeStatus = Field(default=EmployeeStatus.ACTIVE, description="Employment status")
    start_date: date | None = Field(default=None, description="Employment start date")
    manager_email: EmailStr | None = Field(default=None, description="Manager's email address")


class EmployeeBulkImport(BaseModel):
    """DTO for bulk importing employees."""

    employees: list[EmployeeBulkImportItem] = Field(
        max_length=500,
        description="List of employees to import (max 500)",
    )


class EmployeeBulkImportResponse(BaseModel):
    """Response for bulk import operation."""

    created: int = Field(description="Number of employees created")
    updated: int = Field(description="Number of employees updated")
    skipped: int = Field(description="Number of employees skipped")
    errors: list[str] = Field(default_factory=list, description="List of error messages")
