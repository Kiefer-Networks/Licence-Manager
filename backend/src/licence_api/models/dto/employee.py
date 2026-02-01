"""Employee DTOs."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from licence_api.models.domain.employee import EmployeeStatus


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
    start_date: date | None = None
    termination_date: date | None = None
    avatar: str | None = None  # Base64 data URL or None if no avatar
    license_count: int = 0
    manager: ManagerInfo | None = None
    synced_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class EmployeeListResponse(BaseModel):
    """Employee list response DTO."""

    items: list[EmployeeResponse]
    total: int
    page: int
    page_size: int
