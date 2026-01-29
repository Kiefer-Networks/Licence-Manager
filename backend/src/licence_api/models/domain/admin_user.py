"""Admin user domain model."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRole(StrEnum):
    """User role enum."""

    ADMIN = "admin"
    VIEWER = "viewer"


class AdminUser(BaseModel):
    """Admin user domain model."""

    id: UUID
    email: EmailStr
    name: str | None = None
    picture_url: str | None = None
    role: UserRole = UserRole.VIEWER
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
