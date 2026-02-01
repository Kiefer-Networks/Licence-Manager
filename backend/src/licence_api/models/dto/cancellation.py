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
