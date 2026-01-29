"""Provider DTOs."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from licence_api.models.domain.provider import ProviderName, SyncStatus


class ProviderCreate(BaseModel):
    """Provider create DTO."""

    name: str  # Allow any provider name including 'manual'
    display_name: str
    credentials: dict[str, Any] = {}  # Optional for manual providers
    config: dict[str, Any] | None = None


class ProviderUpdate(BaseModel):
    """Provider update DTO."""

    display_name: str | None = None
    enabled: bool | None = None
    credentials: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    payment_method_id: UUID | None = None


class PaymentMethodSummary(BaseModel):
    """Payment method summary for provider response."""

    id: UUID
    name: str
    type: str
    is_expiring: bool = False


class ProviderResponse(BaseModel):
    """Provider response DTO."""

    id: UUID
    name: str  # Allow any provider name including 'manual'
    display_name: str
    enabled: bool
    config: dict[str, Any] | None = None
    last_sync_at: datetime | None = None
    last_sync_status: SyncStatus | None = None
    license_count: int = 0
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
