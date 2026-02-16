"""Audit log router."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from licence_api.dependencies import get_audit_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.audit import (
    ActionsResponse,
    AuditLogListResponse,
    AuditLogResponse,
    AuditUsersListResponse,
    ResourceTypesResponse,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import API_DEFAULT_LIMIT, EXPENSIVE_READ_LIMIT, limiter
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType

router = APIRouter()

# Export limit to prevent DoS via large exports
MAX_EXPORT_RECORDS = 10000

# Whitelists for audit filter validation
ALLOWED_ACTIONS = {
    AuditAction.LOGIN,
    AuditAction.LOGIN_FAILED,
    AuditAction.LOGOUT,
    AuditAction.LOGOUT_ALL,
    AuditAction.PASSWORD_CHANGE,
    AuditAction.PASSWORD_RESET,
    AuditAction.USER_CREATE,
    AuditAction.USER_UPDATE,
    AuditAction.USER_DELETE,
    AuditAction.ROLE_ASSIGN,
    AuditAction.ROLE_REVOKE,
    AuditAction.PROVIDER_CREATE,
    AuditAction.PROVIDER_UPDATE,
    AuditAction.PROVIDER_DELETE,
    AuditAction.PROVIDER_SYNC,
    AuditAction.LICENSE_ASSIGN,
    AuditAction.LICENSE_UNASSIGN,
    AuditAction.LICENSE_UPDATE,
    AuditAction.SETTINGS_UPDATE,
    AuditAction.EXPORT,
    AuditAction.IMPORT,
    # Lifecycle actions
    AuditAction.LICENSE_CANCEL,
    AuditAction.LICENSE_RENEW,
    AuditAction.LICENSE_NEEDS_REORDER,
    AuditAction.PACKAGE_CANCEL,
    AuditAction.PACKAGE_RENEW,
    AuditAction.PACKAGE_NEEDS_REORDER,
    AuditAction.ORG_LICENSE_CANCEL,
    AuditAction.ORG_LICENSE_RENEW,
    AuditAction.ORG_LICENSE_NEEDS_REORDER,
}
ALLOWED_RESOURCE_TYPES = {
    ResourceType.USER,
    ResourceType.ROLE,
    ResourceType.PERMISSION,
    ResourceType.PROVIDER,
    ResourceType.LICENSE,
    ResourceType.EMPLOYEE,
    ResourceType.SETTINGS,
    ResourceType.SETTING,
    ResourceType.NOTIFICATION_RULE,
    ResourceType.PAYMENT_METHOD,
    ResourceType.FILE,
    ResourceType.SESSION,
    ResourceType.SERVICE_ACCOUNT_PATTERN,
    ResourceType.ADMIN_ACCOUNT_PATTERN,
    ResourceType.LICENSE_PACKAGE,
    ResourceType.ORG_LICENSE,
}


@router.get("", response_model=AuditLogListResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_audit_logs(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
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
    return await audit_service.list_audit_logs(
        page=page,
        page_size=page_size,
        action=action,
        resource_type=resource_type,
        admin_user_id=admin_user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        allowed_actions=ALLOWED_ACTIONS,
        allowed_resource_types=ALLOWED_RESOURCE_TYPES,
    )


@router.get("/export")
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def export_audit_logs(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_EXPORT))],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    format: str = Query("csv", pattern="^(csv|json)$"),
    limit: int = Query(MAX_EXPORT_RECORDS, ge=1, le=MAX_EXPORT_RECORDS),
    action: str | None = Query(None, max_length=50),
    resource_type: str | None = Query(None, max_length=50),
    admin_user_id: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    search: str | None = Query(None, min_length=2, max_length=200),
) -> StreamingResponse:
    """Export audit logs as CSV or JSON. Requires audit.export permission.

    Args:
        limit: Number of records to export (1-10000, default 10000)
    """
    content, media_type, filename = await audit_service.export_audit_logs(
        export_format=format,
        limit=limit,
        action=action,
        resource_type=resource_type,
        admin_user_id=admin_user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        allowed_actions=ALLOWED_ACTIONS,
        allowed_resource_types=ALLOWED_RESOURCE_TYPES,
    )

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/users", response_model=AuditUsersListResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def list_audit_users(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> AuditUsersListResponse:
    """Get list of users who have audit log entries. Requires audit.view permission."""
    users = await audit_service.list_audit_users()
    return AuditUsersListResponse(items=users)


@router.get("/resource-types", response_model=ResourceTypesResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def list_resource_types(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> ResourceTypesResponse:
    """Get list of unique resource types. Requires audit.view permission."""
    resource_types = await audit_service.list_resource_types()
    return ResourceTypesResponse(resource_types=resource_types)


@router.get("/actions", response_model=ActionsResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def list_actions(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> ActionsResponse:
    """Get list of unique actions. Requires audit.view permission."""
    actions = await audit_service.list_actions()
    return ActionsResponse(actions=actions)


@router.get("/{log_id}", response_model=AuditLogResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_audit_log(
    request: Request,
    log_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.AUDIT_VIEW))],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> AuditLogResponse:
    """Get a single audit log entry. Requires audit.view permission."""
    result = await audit_service.get_audit_log(log_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )

    return result
