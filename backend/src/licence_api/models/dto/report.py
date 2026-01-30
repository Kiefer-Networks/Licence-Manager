"""Report DTOs."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class MonthlyCost(BaseModel):
    """Monthly cost entry."""

    month: date
    provider_name: str
    cost: Decimal
    currency: str = "EUR"
    license_count: int


class CostReportResponse(BaseModel):
    """Cost report response DTO."""

    start_date: date
    end_date: date
    total_cost: Decimal
    currency: str = "EUR"
    monthly_costs: list[MonthlyCost]


class InactiveLicenseEntry(BaseModel):
    """Inactive license entry."""

    license_id: str
    provider_id: str
    provider_name: str
    employee_id: str | None = None
    employee_name: str | None = None
    employee_email: str | None = None
    employee_status: str | None = None
    external_user_id: str
    last_activity_at: datetime | None = None
    days_inactive: int
    monthly_cost: Decimal | None = None
    is_external_email: bool = False


class InactiveLicenseReport(BaseModel):
    """Inactive license report response DTO."""

    threshold_days: int
    total_inactive: int
    potential_savings: Decimal
    currency: str = "EUR"
    licenses: list[InactiveLicenseEntry]


class OffboardedEmployee(BaseModel):
    """Offboarded employee with pending licenses."""

    employee_name: str
    employee_email: str
    termination_date: date | None = None
    days_since_offboarding: int
    pending_licenses: list[dict[str, str]]


class OffboardingReport(BaseModel):
    """Offboarding report response DTO."""

    total_offboarded_with_licenses: int
    employees: list[OffboardedEmployee]


class ExternalUserLicense(BaseModel):
    """External user license entry."""

    license_id: str
    provider_id: str
    provider_name: str
    external_user_id: str
    employee_id: str | None = None
    employee_name: str | None = None
    employee_email: str | None = None
    employee_status: str | None = None
    license_type: str | None = None
    monthly_cost: Decimal | None = None


class ExternalUsersReport(BaseModel):
    """External users report response DTO."""

    total_external: int
    licenses: list[ExternalUserLicense]
