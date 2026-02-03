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
from licence_api.security.csrf import CSRFProtected
from licence_api.security.rate_limit import limiter, SENSITIVE_OPERATION_LIMIT
from licence_api.services.admin_account_service import AdminAccountService
from licence_api.services.cache_service import get_cache_service
from licence_api.utils.validation import validate_sort_by

router = APIRouter()

# Allowed sort columns for admin account licenses (whitelist to prevent injection)
ALLOWED_ADMIN_LICENSE_SORT_COLUMNS = {"external_user_id", "synced_at", "created_at"}


class AdminAccountLicenseListResponse(BaseModel):
    """Response for admin account licenses list."""

    items: list[LicenseResponse]
    total: int
    page: int
    page_size: int


def get_admin_account_service(
    db: AsyncSession = Depends(get_db),
) -> AdminAccountService:
    """Get AdminAccountService instance."""
    return AdminAccountService(db)


@router.get("/patterns", response_model=AdminAccountPatternListResponse)
async def list_patterns(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[AdminAccountService, Depends(get_admin_account_service)],
) -> AdminAccountPatternListResponse:
    """List all admin account patterns.

    Requires licenses.view permission.
    """
    return await service.get_all_patterns()


@router.get("/patterns/{pattern_id}", response_model=AdminAccountPatternResponse)
async def get_pattern(
    pattern_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[AdminAccountService, Depends(get_admin_account_service)],
) -> AdminAccountPatternResponse:
    """Get a single admin account pattern by ID.

    Requires licenses.view permission.
    """
    pattern = await service.get_pattern_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found",
        )
    return pattern


@router.post("/patterns", response_model=AdminAccountPatternResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_pattern(
    request: Request,
    data: AdminAccountPatternCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[AdminAccountService, Depends(get_admin_account_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> AdminAccountPatternResponse:
    """Create a new admin account pattern.

    Requires licenses.edit permission.
    """
    # Check if pattern already exists
    existing_patterns = await service.get_all_patterns()
    if any(p.email_pattern == data.email_pattern for p in existing_patterns.items):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pattern with this value already exists",
        )

    return await service.create_pattern(
        data=data,
        created_by=current_user.id,
        request=request,
    )


@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_pattern(
    request: Request,
    pattern_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    service: Annotated[AdminAccountService, Depends(get_admin_account_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> None:
    """Delete an admin account pattern.

    Requires licenses.delete permission.
    Note: This does not unmark existing licenses that were marked by this pattern.
    """
    # Get pattern before deletion for audit
    pattern = await service.get_pattern_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found",
        )

    await service.delete_pattern(
        pattern_id=pattern_id,
        admin_user_id=current_user.id,
        request=request,
        pattern_info={
            "email_pattern": pattern.email_pattern,
            "name": pattern.name,
        },
    )


@router.post("/apply", response_model=ApplyAdminPatternsResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def apply_patterns(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[AdminAccountService, Depends(get_admin_account_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> ApplyAdminPatternsResponse:
    """Apply all patterns to all licenses.

    This will mark any licenses matching a pattern as admin accounts.
    Only updates licenses not already marked as admin accounts.

    Requires licenses.edit permission.
    """
    result = await service.apply_patterns_to_all_licenses(
        admin_user_id=current_user.id,
        request=request,
    )

    # Invalidate dashboard cache
    cache = await get_cache_service()
    await cache.invalidate_dashboard()

    return result


@router.get("/licenses", response_model=AdminAccountLicenseListResponse)
async def list_admin_account_licenses(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[AdminAccountService, Depends(get_admin_account_service)],
    search: str | None = Query(default=None, max_length=200),
    provider_id: UUID | None = None,
    owner_id: UUID | None = None,
    sort_by: str = Query(default="external_user_id", max_length=50),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=50, ge=1, le=200),
) -> AdminAccountLicenseListResponse:
    """List all licenses marked as admin accounts.

    Requires licenses.view permission.

    Args:
        owner_id: Filter by owner employee ID (for employee detail page)
    """
    validated_sort_by = validate_sort_by(sort_by, ALLOWED_ADMIN_LICENSE_SORT_COLUMNS, "external_user_id")
    items, total = await service.get_admin_account_licenses(
        search=search,
        provider_id=provider_id,
        owner_id=owner_id,
        sort_by=validated_sort_by,
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
    service: Annotated[AdminAccountService, Depends(get_admin_account_service)],
) -> OrphanedAdminAccountsResponse:
    """Get admin accounts where the owner has been offboarded.

    These are admin accounts that need attention - the owner is no longer
    active and the admin account license should be reviewed/removed.

    Requires licenses.view permission.
    """
    return await service.get_orphaned_admin_accounts()
