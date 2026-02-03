"""Organization license DTOs."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationLicenseCreate(BaseModel):
    """Create a new organization license."""

    name: str = Field(max_length=255)
    license_type: str | None = Field(default=None, max_length=255)
    quantity: int | None = Field(default=None, ge=1, le=1000000)
    unit: str | None = Field(default=None, max_length=50)
    monthly_cost: Decimal | None = Field(default=None, ge=0, le=100000000)
    currency: str = Field(default="EUR", max_length=3, pattern=r"^[A-Z]{3}$")
    billing_cycle: str | None = Field(default=None, max_length=50)
    renewal_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class OrganizationLicenseUpdate(BaseModel):
    """Update an organization license."""

    name: str | None = Field(default=None, max_length=255)
    license_type: str | None = Field(default=None, max_length=255)
    quantity: int | None = Field(default=None, ge=1, le=1000000)
    unit: str | None = Field(default=None, max_length=50)
    monthly_cost: Decimal | None = Field(default=None, ge=0, le=100000000)
    currency: str | None = Field(default=None, max_length=3, pattern=r"^[A-Z]{3}$")
    billing_cycle: str | None = Field(default=None, max_length=50)
    renewal_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class OrganizationLicenseResponse(BaseModel):
    """Organization license response."""

    id: UUID
    provider_id: UUID
    name: str
    license_type: str | None = None
    quantity: int | None = None
    unit: str | None = None
    monthly_cost: Decimal | None = None
    currency: str = "EUR"
    billing_cycle: str | None = None
    renewal_date: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class OrganizationLicenseListResponse(BaseModel):
    """List of organization licenses."""

    items: list[OrganizationLicenseResponse]
    total: int
    total_monthly_cost: Decimal = Decimal("0")
