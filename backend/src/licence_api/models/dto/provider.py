"""Provider DTOs."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from licence_api.models.domain.provider import SyncStatus


def validate_dict_size(v: dict[str, Any] | None, max_keys: int = 50) -> dict[str, Any] | None:
    """Validate dict size and content."""
    if v is None:
        return v
    if len(v) > max_keys:
        raise ValueError(f"Too many fields (max {max_keys})")
    for key, value in v.items():
        if len(key) > 100:
            raise ValueError("Key too long (max 100)")
        if isinstance(value, str) and len(value) > 10000:
            raise ValueError("Value too long (max 10000)")
    return v


class ProviderCreate(BaseModel):
    """Provider create DTO."""

    name: str = Field(max_length=100)  # Allow any provider name including 'manual'
    display_name: str = Field(max_length=255)
    credentials: dict[str, Any] = Field(default_factory=dict)  # Optional for manual providers
    config: dict[str, Any] | None = None

    @field_validator("credentials", "config")
    @classmethod
    def validate_dicts(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate dict size and content."""
        return validate_dict_size(v)


class ProviderUpdate(BaseModel):
    """Provider update DTO."""

    display_name: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(
        default=None,
        max_length=500,
        pattern=r"^/[a-zA-Z0-9/_.-]+$",  # Only allow internal paths starting with /
    )
    enabled: bool | None = None
    credentials: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    payment_method_id: UUID | None = None

    @field_validator("credentials", "config")
    @classmethod
    def validate_dicts(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate dict size and content."""
        return validate_dict_size(v)


class PaymentMethodSummary(BaseModel):
    """Payment method summary for provider response."""

    id: UUID
    name: str
    type: str
    is_expiring: bool = False


class ProviderLicenseStats(BaseModel):
    """License statistics for a provider."""

    active: int = 0
    assigned: int = 0  # Internal assigned (matched to HRIS)
    external: int = 0  # External email domains
    not_in_hris: int = 0  # Has user (internal email) but not found in HRIS
    unassigned: int = 0  # No user assigned (empty external_user_id)
    service_accounts: int = 0  # Service accounts (intentionally not linked to HRIS)


class ProviderResponse(BaseModel):
    """Provider response DTO."""

    id: UUID
    name: str  # Allow any provider name including 'manual'
    display_name: str
    logo_url: str | None = None
    enabled: bool
    config: dict[str, Any] | None = None
    last_sync_at: datetime | None = None
    last_sync_status: SyncStatus | None = None
    license_count: int = 0
    license_stats: ProviderLicenseStats | None = None
    payment_method_id: UUID | None = None
    payment_method: PaymentMethodSummary | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class ProviderListResponse(BaseModel):
    """Provider list response DTO."""

    items: list[ProviderResponse]
    total: int
