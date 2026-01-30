"""Role domain model."""

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

    class Config:
        """Pydantic config."""

        from_attributes = True


class Role(BaseModel):
    """Role domain model."""

    id: UUID
    code: str
    name: str
    description: str | None = None
    is_system: bool = False
    priority: int = 0
    permissions: list[Permission] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
