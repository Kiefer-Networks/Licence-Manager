"""External account DTO models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ExternalAccountBase(BaseModel):
    """Base external account model."""

    provider_type: str = Field(..., max_length=50, description="Provider type (e.g., 'huggingface')")
    external_username: str = Field(..., max_length=255, description="Username in the external system")
    external_user_id: str | None = Field(None, max_length=255, description="ID in the external system")
    display_name: str | None = Field(None, max_length=255, description="Display name from external system")


class ExternalAccountCreate(ExternalAccountBase):
    """Request model for creating an external account link."""

    employee_id: UUID = Field(..., description="Employee to link to")


class ExternalAccountResponse(ExternalAccountBase):
    """Response model for an external account."""

    id: UUID
    employee_id: UUID
    linked_at: datetime
    linked_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExternalAccountListResponse(BaseModel):
    """Response model for listing external accounts."""

    accounts: list[ExternalAccountResponse]
    total: int


class EmployeeSuggestion(BaseModel):
    """Suggestion for linking a license to an employee."""

    employee_id: str
    email: str
    full_name: str
    department: str | None
    confidence: float = Field(..., ge=0, le=1, description="Match confidence score")


class SuggestionsRequest(BaseModel):
    """Request for employee suggestions."""

    display_name: str = Field(..., min_length=1, max_length=255)
    provider_type: str = Field(..., min_length=1, max_length=100)
    limit: int = Field(5, ge=1, le=20)


class SuggestionsResponse(BaseModel):
    """Response with employee suggestions."""

    suggestions: list[EmployeeSuggestion]


class BulkLinkRequest(BaseModel):
    """Request for bulk linking accounts."""

    links: list[ExternalAccountCreate] = Field(max_length=100)


class BulkLinkResponse(BaseModel):
    """Response for bulk link operation."""

    linked: int
    skipped: int
    errors: list[str]


class UsernameMatchingSettingResponse(BaseModel):
    """Response for username matching setting."""

    enabled: bool


class UsernameMatchingSettingUpdate(BaseModel):
    """Request to update username matching setting."""

    enabled: bool
