"""Dashboard DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ProviderSummary(BaseModel):
    """Provider summary for dashboard."""

    id: str
    name: str
    display_name: str
    total_licenses: int
    active_licenses: int
    inactive_licenses: int
    monthly_cost: Decimal | None = None
    currency: str = "EUR"
    last_sync_at: datetime | None = None


class RecentOffboarding(BaseModel):
    """Recent offboarding entry."""

    employee_id: str
    employee_name: str
    employee_email: str
    termination_date: datetime | None = None
    pending_licenses: int
    provider_names: list[str]


class UnassignedLicense(BaseModel):
    """Unassigned license entry."""

    id: str  # License UUID for actions
    provider_name: str
    provider_type: str  # Provider name (e.g., "cursor") for determining if removable
    external_user_id: str
    license_type: str | None = None
    monthly_cost: Decimal | None = None


class DashboardResponse(BaseModel):
    """Dashboard response DTO."""

    total_employees: int
    active_employees: int
    offboarded_employees: int
    total_licenses: int
    active_licenses: int
    unassigned_licenses: int
    total_monthly_cost: Decimal
    potential_savings: Decimal = Decimal("0")
    currency: str = "EUR"
    providers: list[ProviderSummary]
    recent_offboardings: list[RecentOffboarding]
    unassigned_license_samples: list[UnassignedLicense]
