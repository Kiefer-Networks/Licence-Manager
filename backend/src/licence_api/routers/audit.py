"""Audit log router."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.orm.audit_log import AuditLogORM
from licence_api.models.orm.admin_user import AdminUserORM
from licence_api.repositories.audit_repository import AuditRepository
from licence_api.security.auth import require_permission, Permissions

router = APIRouter()


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


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    admin_user_id: UUID | None = Query(None),
) -> AuditLogListResponse:
    """List audit logs with optional filters. Requires audit.view permission."""
    repo = AuditRepository(db)
    offset = (page - 1) * page_size

    # Get logs with filters
    logs, total = await repo.get_recent(
        limit=page_size,
        offset=offset,
        action=action,
        resource_type=resource_type,
    )

    # Filter by admin_user_id if provided (done separately since repo doesn't support this filter)
    if admin_user_id:
        logs = [log for log in logs if log.admin_user_id == admin_user_id]
        total = len(logs)

    # Fetch admin user emails for the logs
    user_ids = {log.admin_user_id for log in logs if log.admin_user_id}
    user_emails: dict[UUID, str] = {}

    if user_ids:
        result = await db.execute(
            select(AdminUserORM.id, AdminUserORM.email).where(
                AdminUserORM.id.in_(user_ids)
            )
        )
        for row in result.all():
            user_emails[row.id] = row.email

    items = [
        AuditLogResponse(
            id=log.id,
            admin_user_id=log.admin_user_id,
            admin_user_email=user_emails.get(log.admin_user_id) if log.admin_user_id else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            changes=log.changes,
            ip_address=str(log.ip_address) if log.ip_address else None,
            created_at=log.created_at,
        )
        for log in logs
    ]

    total_pages = (total + page_size - 1) // page_size

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/resource-types", response_model=ResourceTypesResponse)
async def list_resource_types(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResourceTypesResponse:
    """Get list of unique resource types. Requires audit.view permission."""
    from sqlalchemy import distinct

    result = await db.execute(
        select(distinct(AuditLogORM.resource_type)).order_by(AuditLogORM.resource_type)
    )
    resource_types = [row[0] for row in result.all()]

    return ResourceTypesResponse(resource_types=resource_types)


@router.get("/actions", response_model=ActionsResponse)
async def list_actions(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ActionsResponse:
    """Get list of unique actions. Requires audit.view permission."""
    from sqlalchemy import distinct

    result = await db.execute(
        select(distinct(AuditLogORM.action)).order_by(AuditLogORM.action)
    )
    actions = [row[0] for row in result.all()]

    return ActionsResponse(actions=actions)


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogResponse:
    """Get a single audit log entry. Requires audit.view permission."""
    from fastapi import HTTPException, status

    repo = AuditRepository(db)
    log = await repo.get(log_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )

    # Get admin user email
    admin_email = None
    if log.admin_user_id:
        result = await db.execute(
            select(AdminUserORM.email).where(AdminUserORM.id == log.admin_user_id)
        )
        row = result.first()
        if row:
            admin_email = row.email

    return AuditLogResponse(
        id=log.id,
        admin_user_id=log.admin_user_id,
        admin_user_email=admin_email,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        changes=log.changes,
        ip_address=str(log.ip_address) if log.ip_address else None,
        created_at=log.created_at,
    )
