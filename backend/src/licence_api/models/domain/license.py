"""License domain model."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class LicenseStatus(StrEnum):
    """License status enum."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    UNASSIGNED = "unassigned"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class License(BaseModel):
    """License domain model."""

    id: UUID
    provider_id: UUID
    employee_id: UUID | None = None
    external_user_id: str
    license_type: str | None = None
    status: LicenseStatus
    assigned_at: datetime | None = None
    last_activity_at: datetime | None = None
    monthly_cost: Decimal | None = None
    currency: str = "EUR"
    metadata: dict[str, Any] | None = None
    synced_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
