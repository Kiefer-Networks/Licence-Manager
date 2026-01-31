"""Admin Accounts router for managing admin account patterns and detecting orphans."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.admin_account import (
    AdminAccountPatternCreate,
    AdminAccountPatternListResponse,
    AdminAccountPatternResponse,
    ApplyAdminPatternsResponse,
    OrphanedAdminAccountsResponse,
)
from licence_api.models.dto.license import LicenseResponse
from licence_api.security.auth import require_permission, Permissions
from licence_api.services.admin_account_service import AdminAccountService
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
from licence_api.services.cache_service import get_cache_service

router = APIRouter()


class AdminAccountLicenseListResponse(BaseModel):
    """Response for admin account licenses list."""

    items: list[LicenseResponse]
    total: int
    page: int
    page_size: int


@router.get("/patterns", response_model=AdminAccountPatternListResponse)
async def list_patterns(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminAccountPatternListResponse:
    """List all admin account patterns.

    Requires licenses.view permission.
    """
    service = AdminAccountService(db)
    return await service.get_all_patterns()


@router.get("/patterns/{pattern_id}", response_model=AdminAccountPatternResponse)
async def get_pattern(
    pattern_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminAccountPatternResponse:
    """Get a single admin account pattern by ID.

    Requires licenses.view permission.
    """
    service = AdminAccountService(db)
    pattern = await service.get_pattern_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found",
        )
    return pattern


@router.post("/patterns", response_model=AdminAccountPatternResponse, status_code=status.HTTP_201_CREATED)
async def create_pattern(
    http_request: Request,
    data: AdminAccountPatternCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminAccountPatternResponse:
    """Create a new admin account pattern.

    Requires licenses.edit permission.
    """
    service = AdminAccountService(db)
    audit_service = AuditService(db)

    # Check if pattern already exists
    existing_patterns = await service.get_all_patterns()
    if any(p.email_pattern == data.email_pattern for p in existing_patterns.items):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pattern '{data.email_pattern}' already exists",
        )

    pattern = await service.create_pattern(data, created_by=current_user.id)

    # Audit log the creation
    await audit_service.log(
        action=AuditAction.ADMIN_ACCOUNT_PATTERN_CREATE,
        resource_type=ResourceType.ADMIN_ACCOUNT_PATTERN,
        resource_id=pattern.id,
        admin_user_id=current_user.id,
        changes={
            "email_pattern": data.email_pattern,
            "name": data.name,
            "owner_id": str(data.owner_id) if data.owner_id else None,
        },
        request=http_request,
    )

    await db.commit()

    return pattern


@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern(
    http_request: Request,
    pattern_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete an admin account pattern.

    Requires licenses.edit permission.
    Note: This does not unmark existing licenses that were marked by this pattern.
    """
    service = AdminAccountService(db)
    audit_service = AuditService(db)

    # Get pattern before deletion for audit
    pattern = await service.get_pattern_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found",
        )

    await service.delete_pattern(pattern_id)

    # Audit log the deletion
    await audit_service.log(
        action=AuditAction.ADMIN_ACCOUNT_PATTERN_DELETE,
        resource_type=ResourceType.ADMIN_ACCOUNT_PATTERN,
        resource_id=pattern_id,
        admin_user_id=current_user.id,
        changes={
            "email_pattern": pattern.email_pattern,
            "name": pattern.name,
        },
        request=http_request,
    )

    await db.commit()


@router.post("/apply", response_model=ApplyAdminPatternsResponse)
async def apply_patterns(
    http_request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplyAdminPatternsResponse:
    """Apply all patterns to all licenses.

    This will mark any licenses matching a pattern as admin accounts.
    Only updates licenses not already marked as admin accounts.

    Requires licenses.edit permission.
    """
    service = AdminAccountService(db)
    audit_service = AuditService(db)

    result = await service.apply_patterns_to_all_licenses()

    # Audit log the application
    await audit_service.log(
        action=AuditAction.ADMIN_ACCOUNT_PATTERNS_APPLY,
        resource_type=ResourceType.ADMIN_ACCOUNT_PATTERN,
        admin_user_id=current_user.id,
        changes={
            "updated_count": result.updated_count,
            "patterns_applied": result.patterns_applied,
        },
        request=http_request,
    )

    # Invalidate dashboard cache
    cache = await get_cache_service()
    await cache.invalidate_dashboard()

    await db.commit()

    return result


@router.get("/licenses", response_model=AdminAccountLicenseListResponse)
async def list_admin_account_licenses(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None, max_length=200),
    provider_id: UUID | None = None,
    sort_by: str = Query(default="external_user_id", max_length=50),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=50, ge=1, le=200),
) -> AdminAccountLicenseListResponse:
    """List all licenses marked as admin accounts.

    Requires licenses.view permission.
    """
    service = AdminAccountService(db)
    items, total = await service.get_admin_account_licenses(
        search=search,
        provider_id=provider_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )

    return AdminAccountLicenseListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/orphaned", response_model=OrphanedAdminAccountsResponse)
async def get_orphaned_admin_accounts(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrphanedAdminAccountsResponse:
    """Get admin accounts where the owner has been offboarded.

    These are admin accounts that need attention - the owner is no longer
    active and the admin account license should be reviewed/removed.

    Requires licenses.view permission.
    """
    service = AdminAccountService(db)
    return await service.get_orphaned_admin_accounts()
