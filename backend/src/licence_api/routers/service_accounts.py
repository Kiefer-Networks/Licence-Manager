"""Service Accounts router for managing global service account patterns."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.license import LicenseResponse
from licence_api.models.dto.service_account import (
    ApplyPatternsResponse,
    ServiceAccountPatternCreate,
    ServiceAccountPatternListResponse,
    ServiceAccountPatternResponse,
)
from licence_api.security.auth import require_permission, Permissions
from licence_api.services.cache_service import get_cache_service
from licence_api.services.service_account_service import ServiceAccountService
from licence_api.utils.validation import validate_sort_by

router = APIRouter()

# Allowed sort columns for service account licenses (whitelist to prevent injection)
ALLOWED_SERVICE_LICENSE_SORT_COLUMNS = {"external_user_id", "synced_at", "created_at"}


class ServiceAccountLicenseListResponse(BaseModel):
    """Response for service account licenses list."""

    items: list[LicenseResponse]
    total: int
    page: int
    page_size: int


def get_service_account_service(
    db: AsyncSession = Depends(get_db),
) -> ServiceAccountService:
    """Get ServiceAccountService instance."""
    return ServiceAccountService(db)


@router.get("/patterns", response_model=ServiceAccountPatternListResponse)
async def list_patterns(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
) -> ServiceAccountPatternListResponse:
    """List all service account patterns.

    Requires licenses.view permission.
    """
    return await service.get_all_patterns()


@router.get("/patterns/{pattern_id}", response_model=ServiceAccountPatternResponse)
async def get_pattern(
    pattern_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
) -> ServiceAccountPatternResponse:
    """Get a single service account pattern by ID.

    Requires licenses.view permission.
    """
    pattern = await service.get_pattern_by_id(pattern_id)
    if pattern is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found",
        )
    return pattern


@router.post("/patterns", response_model=ServiceAccountPatternResponse, status_code=status.HTTP_201_CREATED)
async def create_pattern(
    http_request: Request,
    data: ServiceAccountPatternCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
) -> ServiceAccountPatternResponse:
    """Create a new service account pattern.

    Requires licenses.edit permission.
    """
    # Check if pattern already exists
    existing_patterns = await service.get_all_patterns()
    if any(p.email_pattern == data.email_pattern for p in existing_patterns.items):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pattern '{data.email_pattern}' already exists",
        )

    return await service.create_pattern(
        data=data,
        created_by=current_user.id,
        request=http_request,
    )


@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern(
    http_request: Request,
    pattern_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
) -> None:
    """Delete a service account pattern.

    Requires licenses.edit permission.
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
        request=http_request,
        pattern_info={
            "email_pattern": pattern.email_pattern,
            "name": pattern.name,
        },
    )


@router.post("/apply", response_model=ApplyPatternsResponse)
async def apply_patterns(
    http_request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
) -> ApplyPatternsResponse:
    """Apply all patterns to all licenses.

    This will mark any licenses matching a pattern as service accounts.
    Only updates licenses not already marked as service accounts.

    Requires licenses.edit permission.
    """
    result = await service.apply_patterns_to_all_licenses(
        admin_user_id=current_user.id,
        request=http_request,
    )

    # Invalidate dashboard cache
    cache = await get_cache_service()
    await cache.invalidate_dashboard()

    return result


@router.get("/licenses", response_model=ServiceAccountLicenseListResponse)
async def list_service_account_licenses(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
    search: str | None = Query(default=None, max_length=200),
    provider_id: UUID | None = None,
    sort_by: str = Query(default="external_user_id", max_length=50),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=50, ge=1, le=200),
) -> ServiceAccountLicenseListResponse:
    """List all licenses marked as service accounts.

    Requires licenses.view permission.
    """
    validated_sort_by = validate_sort_by(sort_by, ALLOWED_SERVICE_LICENSE_SORT_COLUMNS, "external_user_id")
    items, total = await service.get_service_account_licenses(
        search=search,
        provider_id=provider_id,
        sort_by=validated_sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )

    return ServiceAccountLicenseListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
