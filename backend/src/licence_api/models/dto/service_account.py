"""Service Account Pattern DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceAccountPatternCreate(BaseModel):
    """DTO for creating a new service account pattern."""

    email_pattern: str = Field(
        max_length=255,
        min_length=1,
        pattern=r"^[a-zA-Z0-9.*@_+-]+$",  # Safe pattern chars: alphanumeric, wildcards, email chars
    )
    name: str | None = Field(default=None, max_length=255)
    owner_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ServiceAccountPatternUpdate(BaseModel):
    """DTO for updating a service account pattern."""

    email_pattern: str | None = Field(default=None, max_length=255)
    name: str | None = Field(default=None, max_length=255)
    owner_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ServiceAccountPatternResponse(BaseModel):
    """DTO for service account pattern response."""

    id: UUID
    email_pattern: str
    name: str | None
    owner_id: UUID | None
    owner_name: str | None = None
    notes: str | None
    created_at: datetime
    created_by: UUID | None
    created_by_name: str | None = None
    match_count: int = 0  # Number of licenses matching this pattern

    class Config:
        """Pydantic config."""

        from_attributes = True


class ServiceAccountPatternListResponse(BaseModel):
    """DTO for list of service account patterns."""

    items: list[ServiceAccountPatternResponse]
    total: int


class ApplyPatternsResponse(BaseModel):
    """Response after applying patterns to all licenses."""

    updated_count: int
    patterns_applied: int


# License Type DTOs
class ServiceAccountLicenseTypeCreate(BaseModel):
    """DTO for creating a new service account license type."""

    license_type: str = Field(min_length=1, max_length=500)
    name: str | None = Field(default=None, max_length=255)
    owner_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ServiceAccountLicenseTypeResponse(BaseModel):
    """DTO for service account license type response."""

    id: UUID
    license_type: str
    name: str | None
    owner_id: UUID | None
    owner_name: str | None = None
    notes: str | None
    created_at: datetime
    created_by: UUID | None
    created_by_name: str | None = None
    match_count: int = 0  # Number of licenses matching this license type

    class Config:
        """Pydantic config."""

        from_attributes = True


class ServiceAccountLicenseTypeListResponse(BaseModel):
    """DTO for list of service account license types."""

    items: list[ServiceAccountLicenseTypeResponse]
    total: int


class ApplyLicenseTypesResponse(BaseModel):
    """Response after applying license types to all licenses."""

    updated_count: int
    license_types_applied: int
