"""Audit log router."""

import csv
import io
import json
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.repositories.audit_repository import AuditRepository
from licence_api.repositories.user_repository import UserRepository
from licence_api.security.auth import require_permission, Permissions
from licence_api.services.audit_service import AuditAction, ResourceType
from licence_api.utils.validation import validate_against_whitelist

router = APIRouter()

# Export limit to prevent DoS via large exports
MAX_EXPORT_RECORDS = 10000

# Whitelists for audit filter validation
ALLOWED_ACTIONS = {
    AuditAction.LOGIN, AuditAction.LOGIN_FAILED, AuditAction.LOGOUT,
    AuditAction.LOGOUT_ALL, AuditAction.PASSWORD_CHANGE, AuditAction.PASSWORD_RESET,
    AuditAction.USER_CREATE, AuditAction.USER_UPDATE, AuditAction.USER_DELETE,
    AuditAction.ROLE_ASSIGN, AuditAction.ROLE_REVOKE,
    AuditAction.PROVIDER_CREATE, AuditAction.PROVIDER_UPDATE, AuditAction.PROVIDER_DELETE,
    AuditAction.PROVIDER_SYNC, AuditAction.LICENSE_ASSIGN, AuditAction.LICENSE_UNASSIGN,
    AuditAction.LICENSE_UPDATE, AuditAction.SETTINGS_UPDATE, AuditAction.EXPORT,
    AuditAction.IMPORT,
    # Lifecycle actions
    AuditAction.LICENSE_CANCEL, AuditAction.LICENSE_RENEW, AuditAction.LICENSE_NEEDS_REORDER,
    AuditAction.PACKAGE_CANCEL, AuditAction.PACKAGE_RENEW, AuditAction.PACKAGE_NEEDS_REORDER,
    AuditAction.ORG_LICENSE_CANCEL, AuditAction.ORG_LICENSE_RENEW, AuditAction.ORG_LICENSE_NEEDS_REORDER,
}
ALLOWED_RESOURCE_TYPES = {
    ResourceType.USER, ResourceType.ROLE, ResourceType.PERMISSION,
    ResourceType.PROVIDER, ResourceType.LICENSE, ResourceType.EMPLOYEE,
    ResourceType.SETTINGS, ResourceType.SETTING, ResourceType.NOTIFICATION_RULE,
    ResourceType.PAYMENT_METHOD, ResourceType.FILE, ResourceType.SESSION,
    ResourceType.SERVICE_ACCOUNT_PATTERN, ResourceType.ADMIN_ACCOUNT_PATTERN,
    ResourceType.LICENSE_PACKAGE, ResourceType.ORG_LICENSE,
}


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


# Dependency injection functions
def get_audit_repository(db: AsyncSession = Depends(get_db)) -> AuditRepository:
    """Get AuditRepository instance."""
    return AuditRepository(db)


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get UserRepository instance."""
    return UserRepository(db)


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    action: str | None = Query(None, max_length=50),
    resource_type: str | None = Query(None, max_length=50),
    admin_user_id: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    search: str | None = Query(None, min_length=2, max_length=200),
) -> AuditLogListResponse:
    """List audit logs with optional filters. Requires audit.view permission."""
    # Validate filter inputs against whitelists
    action = validate_against_whitelist(action, ALLOWED_ACTIONS)
    resource_type = validate_against_whitelist(resource_type, ALLOWED_RESOURCE_TYPES)

    offset = (page - 1) * page_size

    # Get logs with all filters
    logs, total = await audit_repo.get_recent(
        limit=page_size,
        offset=offset,
        action=action,
        resource_type=resource_type,
        admin_user_id=admin_user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )

    # Fetch admin user emails via repository
    user_ids = {log.admin_user_id for log in logs if log.admin_user_id}
    user_emails = await user_repo.get_emails_by_ids(user_ids)

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


@router.get("/export")
async def export_audit_logs(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_EXPORT))],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    format: str = Query("csv", pattern="^(csv|json)$"),
    limit: int = Query(MAX_EXPORT_RECORDS, ge=1, le=MAX_EXPORT_RECORDS),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    admin_user_id: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    search: str | None = Query(None, min_length=2, max_length=200),
) -> StreamingResponse:
    """Export audit logs as CSV or JSON. Requires audit.export permission.

    Args:
        limit: Number of records to export (1-10000, default 10000)
    """
    # Validate filter inputs against whitelists
    action = validate_against_whitelist(action, ALLOWED_ACTIONS)
    resource_type = validate_against_whitelist(resource_type, ALLOWED_RESOURCE_TYPES)

    # Get matching logs with user-specified limit (capped at MAX_EXPORT_RECORDS)
    logs, total = await audit_repo.get_recent(
        limit=limit,
        offset=0,
        action=action,
        resource_type=resource_type,
        admin_user_id=admin_user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )

    # Fetch admin user emails
    user_ids = {log.admin_user_id for log in logs if log.admin_user_id}
    user_emails = await user_repo.get_emails_by_ids(user_ids)

    if format == "json":
        # JSON export
        data = [
            {
                "id": str(log.id),
                "timestamp": log.created_at.isoformat(),
                "user_email": user_emails.get(log.admin_user_id) if log.admin_user_id else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "changes": log.changes,
                "ip_address": str(log.ip_address) if log.ip_address else None,
            }
            for log in logs
        ]
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_log.json"},
        )
    else:
        # CSV export
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Timestamp",
            "User",
            "Action",
            "Resource Type",
            "Resource ID",
            "Changes",
            "IP Address",
        ])
        for log in logs:
            writer.writerow([
                log.created_at.isoformat(),
                user_emails.get(log.admin_user_id) if log.admin_user_id else "System",
                log.action,
                log.resource_type,
                str(log.resource_id) if log.resource_id else "",
                json.dumps(log.changes, ensure_ascii=False) if log.changes else "",
                str(log.ip_address) if log.ip_address else "",
            ])
        content = output.getvalue()
        return StreamingResponse(
            iter([content]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
        )


@router.get("/users", response_model=AuditUsersListResponse)
async def list_audit_users(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> AuditUsersListResponse:
    """Get list of users who have audit log entries. Requires audit.view permission."""
    users = await audit_repo.get_distinct_users()
    return AuditUsersListResponse(
        items=[AuditUserResponse(id=user_id, email=email) for user_id, email in users]
    )


@router.get("/resource-types", response_model=ResourceTypesResponse)
async def list_resource_types(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> ResourceTypesResponse:
    """Get list of unique resource types. Requires audit.view permission."""
    resource_types = await audit_repo.get_distinct_resource_types()
    return ResourceTypesResponse(resource_types=resource_types)


@router.get("/actions", response_model=ActionsResponse)
async def list_actions(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> ActionsResponse:
    """Get list of unique actions. Requires audit.view permission."""
    actions = await audit_repo.get_distinct_actions()
    return ActionsResponse(actions=actions)


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuditLogResponse:
    """Get a single audit log entry. Requires audit.view permission."""
    log = await audit_repo.get_by_id(log_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )

    # Get admin user email via repository
    admin_email = None
    if log.admin_user_id:
        admin_email = await user_repo.get_email_by_id(log.admin_user_id)

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
