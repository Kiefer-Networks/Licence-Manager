"""Audit log DTOs."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: UUID
    admin_user_id: UUID | None
    admin_user_email: str | None
    action: str
    resource_type: str
    resource_id: UUID | None
    changes: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ResourceTypesResponse(BaseModel):
    """Available resource types response."""

    resource_types: list[str]


class ActionsResponse(BaseModel):
    """Available actions response."""

    actions: list[str]


class AuditUserResponse(BaseModel):
    """User who has audit entries."""

    id: UUID
    email: str


class AuditUsersListResponse(BaseModel):
    """List of users with audit entries."""

    items: list[AuditUserResponse]
