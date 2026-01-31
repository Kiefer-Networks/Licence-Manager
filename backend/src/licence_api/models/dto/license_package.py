"""License package DTOs."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class LicensePackageCreate(BaseModel):
    """Create a new license package."""

    license_type: str
    display_name: str | None = None
    total_seats: int = Field(ge=1)
    cost_per_seat: Decimal | None = None
    billing_cycle: str | None = None
    payment_frequency: str | None = None
    currency: str = "EUR"
    contract_start: date | None = None
    contract_end: date | None = None
    auto_renew: bool = True
    notes: str | None = None


class LicensePackageUpdate(BaseModel):
    """Update a license package."""

    display_name: str | None = None
    total_seats: int | None = Field(default=None, ge=1)
    cost_per_seat: Decimal | None = None
    billing_cycle: str | None = None
    payment_frequency: str | None = None
    currency: str | None = None
    contract_start: date | None = None
    contract_end: date | None = None
    auto_renew: bool | None = None
    notes: str | None = None


class LicensePackageResponse(BaseModel):
    """License package response with utilization stats."""

    id: UUID
    provider_id: UUID
    license_type: str
    display_name: str | None = None
    total_seats: int
    assigned_seats: int = 0  # Calculated from actual license assignments
    available_seats: int = 0  # total_seats - assigned_seats
    utilization_percent: float = 0.0  # (assigned_seats / total_seats) * 100
    cost_per_seat: Decimal | None = None
    total_monthly_cost: Decimal | None = None  # cost_per_seat * total_seats
    billing_cycle: str | None = None
    payment_frequency: str | None = None
    currency: str = "EUR"
    contract_start: date | None = None
    contract_end: date | None = None
    auto_renew: bool = True
    notes: str | None = None
    # Cancellation tracking
    cancelled_at: datetime | None = None
    cancellation_effective_date: date | None = None
    cancellation_reason: str | None = None
    cancelled_by: UUID | None = None
    needs_reorder: bool = False
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class LicensePackageListResponse(BaseModel):
    """List of license packages."""

    items: list[LicensePackageResponse]
    total: int
