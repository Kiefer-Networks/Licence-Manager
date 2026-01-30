"""Permission domain model."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Permission(BaseModel):
    """Permission domain model."""

    id: UUID
    code: str
    name: str
    description: str | None = None
    category: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
