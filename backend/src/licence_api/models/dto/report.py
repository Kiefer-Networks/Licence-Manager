"""Report DTOs."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

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
    has_currency_mix: bool = False  # True if licenses have different currencies
    currencies_found: list[str] = []  # List of all currencies found


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


# Quick Win DTOs

class ExpiringContract(BaseModel):
    """Expiring contract entry."""

    package_id: str
    provider_id: str
    provider_name: str
    license_type: str
    display_name: str | None = None
    total_seats: int
    contract_end: date
    days_until_expiry: int
    auto_renew: bool
    total_cost: Decimal | None = None
    currency: str = "EUR"


class ExpiringContractsReport(BaseModel):
    """Expiring contracts report response DTO."""

    total_expiring: int
    contracts: list[ExpiringContract]


class ProviderUtilization(BaseModel):
    """Provider utilization entry."""

    provider_id: str
    provider_name: str
    license_type: str | None = None
    purchased_seats: int  # From package or license_info (0 if unknown)
    active_seats: int  # All active licenses
    assigned_seats: int  # Licenses with employee_id
    unassigned_seats: int  # Active without employee_id
    external_seats: int  # External email addresses
    utilization_percent: float  # assigned / active
    monthly_cost: Decimal | None = None  # Total monthly cost
    monthly_waste: Decimal | None = None  # Cost of unassigned seats
    external_cost: Decimal | None = None  # Cost of external seats
    currency: str = "EUR"


class UtilizationReport(BaseModel):
    """License utilization report response DTO."""

    total_purchased: int  # Total from packages/license_info
    total_active: int  # All active licenses
    total_assigned: int  # Licenses with employee_id
    total_unassigned: int  # Active without employee_id
    total_external: int  # External email addresses
    overall_utilization: float
    total_monthly_cost: Decimal  # Total cost
    total_monthly_waste: Decimal  # Cost of unassigned
    total_external_cost: Decimal  # Cost of external licenses
    currency: str = "EUR"
    providers: list[ProviderUtilization]


class CostTrendEntry(BaseModel):
    """Cost trend entry for a single month."""

    month: date
    total_cost: Decimal
    license_count: int
    currency: str = "EUR"


class CostTrendReport(BaseModel):
    """Cost trend report response DTO."""

    months: list[CostTrendEntry]
    trend_direction: str  # "up", "down", "stable"
    percent_change: float  # Change from first to last month
    currency: str = "EUR"
    has_data: bool = True  # False when no historical snapshots exist


class DuplicateAccount(BaseModel):
    """Duplicate account entry."""

    email: str
    occurrences: int
    providers: list[str]
    names: list[str]
    license_ids: list[str]
    total_monthly_cost: Decimal | None = None


class DuplicateAccountsReport(BaseModel):
    """Duplicate accounts report response DTO."""

    total_duplicates: int
    potential_savings: Decimal
    currency: str = "EUR"
    duplicates: list[DuplicateAccount]


# ==================== COST BREAKDOWN REPORTS ====================


class DepartmentCost(BaseModel):
    """Cost breakdown for a single department."""

    department: str
    employee_count: int
    license_count: int
    total_monthly_cost: Decimal
    cost_per_employee: Decimal
    top_providers: list[str]  # Top 3 providers by cost
    currency: str = "EUR"


class CostsByDepartmentReport(BaseModel):
    """Costs grouped by department."""

    total_departments: int
    total_monthly_cost: Decimal
    average_cost_per_employee: Decimal
    currency: str = "EUR"
    departments: list[DepartmentCost]


class EmployeeLicense(BaseModel):
    """License info for employee cost report."""

    provider_name: str
    license_type: str | None = None
    monthly_cost: Decimal | None = None


class EmployeeCost(BaseModel):
    """Cost breakdown for a single employee."""

    employee_id: str
    employee_name: str
    employee_email: str
    department: str | None = None
    status: str
    license_count: int
    total_monthly_cost: Decimal
    licenses: list[EmployeeLicense]
    currency: str = "EUR"


class CostsByEmployeeReport(BaseModel):
    """Costs grouped by employee."""

    total_employees: int
    total_monthly_cost: Decimal
    average_cost_per_employee: Decimal
    median_cost_per_employee: Decimal
    max_cost_employee: str | None = None  # Name of highest cost employee
    currency: str = "EUR"
    employees: list[EmployeeCost]


# ==================== LICENSE LIFECYCLE REPORTS ====================


class ExpiringLicense(BaseModel):
    """Expiring license entry."""

    license_id: UUID
    provider_id: UUID
    provider_name: str
    external_user_id: str
    license_type: str | None = None
    employee_id: UUID | None = None
    employee_name: str | None = None
    expires_at: date
    days_until_expiry: int
    monthly_cost: Decimal | None = None
    needs_reorder: bool = False
    status: str = "active"


class ExpiringLicensesReport(BaseModel):
    """Expiring licenses report response DTO."""

    total_expiring: int
    expiring_within_30_days: int
    expiring_within_90_days: int
    needs_reorder_count: int
    licenses: list[ExpiringLicense]


class CancelledLicense(BaseModel):
    """Cancelled license entry."""

    license_id: UUID
    provider_id: UUID
    provider_name: str
    external_user_id: str
    license_type: str | None = None
    employee_id: UUID | None = None
    employee_name: str | None = None
    cancelled_at: datetime
    cancellation_effective_date: date
    cancellation_reason: str | None = None
    cancelled_by_name: str | None = None
    monthly_cost: Decimal | None = None
    is_effective: bool = False  # True if effective_date has passed


class CancelledLicensesReport(BaseModel):
    """Cancelled licenses report response DTO."""

    total_cancelled: int
    pending_effective: int  # Not yet effective
    already_effective: int  # Already passed effective date
    licenses: list[CancelledLicense]


class LicenseLifecycleOverview(BaseModel):
    """License lifecycle overview response DTO."""

    total_active: int
    total_expiring_soon: int  # Within 90 days
    total_expired: int
    total_cancelled: int
    total_needs_reorder: int
    expiring_licenses: list[ExpiringLicense]
    cancelled_licenses: list[CancelledLicense]
