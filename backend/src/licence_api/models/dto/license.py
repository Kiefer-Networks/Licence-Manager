"""License DTOs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from licence_api.models.domain.license import LicenseStatus


class LicenseResponse(BaseModel):
    """License response DTO."""

    id: UUID
    provider_id: UUID
    provider_name: str
    employee_id: UUID | None = None
    employee_email: str | None = None
    employee_name: str | None = None
    external_user_id: str
    license_type: str | None = None
    license_type_display_name: str | None = None  # Custom display name from pricing config
    status: LicenseStatus
    assigned_at: datetime | None = None
    last_activity_at: datetime | None = None
    monthly_cost: Decimal | None = None
    currency: str = "EUR"
    metadata: dict[str, Any] | None = None
    synced_at: datetime
    is_external_email: bool = False
    employee_status: str | None = None  # active, offboarded, etc.
    # Service account fields
    is_service_account: bool = False
    service_account_name: str | None = None
    service_account_owner_id: UUID | None = None
    service_account_owner_name: str | None = None
    # Admin account fields (personal admin accounts linked to employees)
    is_admin_account: bool = False
    admin_account_name: str | None = None
    admin_account_owner_id: UUID | None = None
    admin_account_owner_name: str | None = None
    admin_account_owner_status: str | None = None  # active, offboarded - for warning display
    # Match fields
    suggested_employee_id: UUID | None = None
    suggested_employee_name: str | None = None
    suggested_employee_email: str | None = None
    match_confidence: float | None = None
    # auto_matched, suggested, confirmed, rejected, external_guest, external_review
    match_status: str | None = None
    match_method: str | None = None  # exact_email, alias, local_part, fuzzy_name
    # Expiration tracking
    expires_at: date | None = None
    needs_reorder: bool = False
    # Cancellation tracking
    cancelled_at: datetime | None = None
    cancellation_effective_date: date | None = None
    cancellation_reason: str | None = None
    cancelled_by: UUID | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class LicenseListResponse(BaseModel):
    """License list response DTO."""

    items: list[LicenseResponse]
    total: int
    page: int
    page_size: int


class LicenseStats(BaseModel):
    """License statistics for categorized view."""

    total_active: int
    total_assigned: int
    total_unassigned: int  # Licenses with no user assigned (empty external_user_id)
    total_not_in_hris: int = 0  # Has user (internal email) but not found in HRIS
    total_inactive: int
    total_external: int
    total_service_accounts: int = 0
    total_admin_accounts: int = 0
    total_orphaned_admin_accounts: int = 0  # Admin accounts with offboarded owners
    total_suggested: int = 0  # Licenses with suggested matches
    total_external_review: int = 0  # External licenses needing review
    total_external_guest: int = 0  # Confirmed external guests
    monthly_cost: Decimal
    potential_savings: Decimal  # Unassigned + offboarded licenses
    currency: str = "EUR"
    has_currency_mix: bool = False  # True if licenses have different currencies
    currencies_found: list[str] = []  # List of all currencies found


class CategorizedLicensesResponse(BaseModel):
    """Response with licenses categorized into assigned/unassigned/external/service_accounts."""

    assigned: list[LicenseResponse]
    unassigned: list[LicenseResponse]  # Licenses with no user assigned (empty external_user_id)
    not_in_hris: list[LicenseResponse] = []  # Has user (internal email) but not found in HRIS
    external: list[LicenseResponse]
    service_accounts: list[LicenseResponse]
    admin_accounts: list[LicenseResponse] = []  # Personal admin accounts
    orphaned_admin_accounts: list[LicenseResponse] = []  # Admin accounts with offboarded owners
    # New categories for match workflow
    suggested: list[LicenseResponse] = []  # Licenses with suggested matches
    external_review: list[LicenseResponse] = []  # External licenses needing review
    external_guest: list[LicenseResponse] = []  # Confirmed external guests
    stats: LicenseStats


class ServiceAccountUpdate(BaseModel):
    """Update service account status for a license."""

    is_service_account: bool
    service_account_name: str | None = Field(default=None, max_length=255)
    service_account_owner_id: UUID | None = None
    apply_globally: bool = False  # Add email to global service account patterns


class AdminAccountUpdate(BaseModel):
    """Update admin account status for a license."""

    is_admin_account: bool
    admin_account_name: str | None = Field(default=None, max_length=255)
    admin_account_owner_id: UUID | None = None
    apply_globally: bool = False  # Add email to global admin account patterns


class LicenseTypeUpdate(BaseModel):
    """Update license type for a license."""

    license_type: str = Field(max_length=100)
