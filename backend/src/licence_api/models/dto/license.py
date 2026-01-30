"""License DTOs."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

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
    total_unassigned: int
    total_inactive: int
    total_external: int
    total_service_accounts: int = 0
    monthly_cost: Decimal
    potential_savings: Decimal  # Unassigned + offboarded licenses
    currency: str = "EUR"


class CategorizedLicensesResponse(BaseModel):
    """Response with licenses categorized into assigned/unassigned/external/service_accounts."""

    assigned: list[LicenseResponse]
    unassigned: list[LicenseResponse]
    external: list[LicenseResponse]
    service_accounts: list[LicenseResponse]
    stats: LicenseStats


class ServiceAccountUpdate(BaseModel):
    """Update service account status for a license."""

    is_service_account: bool
    service_account_name: str | None = None
    service_account_owner_id: UUID | None = None
