"""Admin Account DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminAccountPatternCreate(BaseModel):
    """Create a new admin account pattern."""

    email_pattern: str = Field(max_length=255)
    name: str | None = None
    owner_id: UUID | None = None
    notes: str | None = None


class AdminAccountPatternUpdate(BaseModel):
    """Update an admin account pattern."""

    name: str | None = None
    owner_id: UUID | None = None
    notes: str | None = None


class AdminAccountPatternResponse(BaseModel):
    """Admin account pattern response."""

    id: UUID
    email_pattern: str
    name: str | None
    owner_id: UUID | None
    owner_name: str | None = None
    notes: str | None
    created_at: datetime
    created_by: UUID | None
    created_by_name: str | None = None
    match_count: int = 0


class AdminAccountPatternListResponse(BaseModel):
    """List of admin account patterns."""

    items: list[AdminAccountPatternResponse]
    total: int


class ApplyAdminPatternsResponse(BaseModel):
    """Response after applying admin patterns to licenses."""

    updated_count: int
    patterns_applied: int


class AdminAccountUpdate(BaseModel):
    """Update admin account status on a license."""

    is_admin_account: bool
    admin_account_name: str | None = None
    admin_account_owner_id: UUID | None = None
    apply_globally: bool = False


class OrphanedAdminAccountWarning(BaseModel):
    """Warning for admin account with offboarded owner."""

    license_id: UUID
    external_user_id: str
    provider_id: UUID
    provider_name: str
    admin_account_name: str | None
    owner_id: UUID
    owner_name: str
    owner_email: str
    offboarded_at: datetime | None


class OrphanedAdminAccountsResponse(BaseModel):
    """List of orphaned admin accounts (owners offboarded)."""

    items: list[OrphanedAdminAccountWarning]
    total: int
