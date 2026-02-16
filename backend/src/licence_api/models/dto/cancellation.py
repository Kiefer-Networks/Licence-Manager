"""Cancellation and renewal DTOs."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CancellationRequest(BaseModel):
    """Request to cancel a license/package."""

    effective_date: date
    reason: str | None = Field(default=None, max_length=2000)


class CancellationResponse(BaseModel):
    """Response after cancellation."""

    id: UUID
    cancelled_at: datetime
    cancellation_effective_date: date
    cancellation_reason: str | None = None
    cancelled_by: UUID | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class RenewRequest(BaseModel):
    """Request to renew a license/package."""

    new_expiration_date: date
    clear_cancellation: bool = True


class NeedsReorderUpdate(BaseModel):
    """Update needs_reorder flag."""

    needs_reorder: bool


class RenewalResponse(BaseModel):
    """Response after renewal of a license, package, or organization license."""

    success: bool = True
    message: str
    expires_at: str | None = None
    contract_end: str | None = None
    renewal_date: str | None = None
    status: str | None = None


class NeedsReorderResponse(BaseModel):
    """Response after updating the needs_reorder flag."""

    success: bool = True
    needs_reorder: bool
