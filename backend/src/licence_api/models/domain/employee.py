"""Employee domain model."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr


class EmployeeStatus(StrEnum):
    """Employee status enum."""

    ACTIVE = "active"
    OFFBOARDED = "offboarded"


class Employee(BaseModel):
    """Employee domain model."""

    id: UUID
    hibob_id: str
    email: EmailStr
    full_name: str
    department: str | None = None
    status: EmployeeStatus
    start_date: date | None = None
    termination_date: date | None = None
    manager_email: str | None = None
    manager_id: UUID | None = None
    synced_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
