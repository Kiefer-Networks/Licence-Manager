"""Organization license DTOs."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class OrganizationLicenseCreate(BaseModel):
    """Create a new organization license."""

    name: str
    license_type: str | None = None
    quantity: int | None = None
    unit: str | None = None
    monthly_cost: Decimal | None = None
    currency: str = "EUR"
    billing_cycle: str | None = None
    renewal_date: date | None = None
    notes: str | None = None


class OrganizationLicenseUpdate(BaseModel):
    """Update an organization license."""

    name: str | None = None
    license_type: str | None = None
    quantity: int | None = None
    unit: str | None = None
    monthly_cost: Decimal | None = None
    currency: str | None = None
    billing_cycle: str | None = None
    renewal_date: date | None = None
    notes: str | None = None


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
