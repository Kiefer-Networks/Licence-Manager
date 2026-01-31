"""Service Account Pattern DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceAccountPatternCreate(BaseModel):
    """DTO for creating a new service account pattern."""

    email_pattern: str = Field(max_length=255)
    name: str | None = None
    owner_id: UUID | None = None
    notes: str | None = None


class ServiceAccountPatternUpdate(BaseModel):
    """DTO for updating a service account pattern."""

    email_pattern: str | None = Field(default=None, max_length=255)
    name: str | None = None
    owner_id: UUID | None = None
    notes: str | None = None


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
