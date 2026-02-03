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
    ApplyLicenseTypesResponse,
    ApplyPatternsResponse,
    ServiceAccountLicenseTypeCreate,
    ServiceAccountLicenseTypeListResponse,
    ServiceAccountLicenseTypeResponse,
    ServiceAccountPatternCreate,
    ServiceAccountPatternListResponse,
    ServiceAccountPatternResponse,
)
from licence_api.security.auth import require_permission, Permissions
from licence_api.security.csrf import CSRFProtected
from licence_api.security.rate_limit import limiter, SENSITIVE_OPERATION_LIMIT
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
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_pattern(
    http_request: Request,
    data: ServiceAccountPatternCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> ServiceAccountPatternResponse:
    """Create a new service account pattern.

    Requires licenses.edit permission.
    """
    # Check if pattern already exists
    existing_patterns = await service.get_all_patterns()
    if any(p.email_pattern == data.email_pattern for p in existing_patterns.items):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An email pattern with this value already exists",
        )

    return await service.create_pattern(
        data=data,
        created_by=current_user.id,
        request=http_request,
    )


@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_pattern(
    request: Request,
    pattern_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> None:
    """Delete a service account pattern.

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


@router.post("/apply", response_model=ApplyPatternsResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def apply_patterns(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> ApplyPatternsResponse:
    """Apply all patterns to all licenses.

    This will mark any licenses matching a pattern as service accounts.
    Only updates licenses not already marked as service accounts.

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


# License Type endpoints
@router.get("/license-types", response_model=ServiceAccountLicenseTypeListResponse)
async def list_license_types(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
) -> ServiceAccountLicenseTypeListResponse:
    """List all service account license types.

    Requires licenses.view permission.
    """
    return await service.get_all_license_types()


@router.get("/license-types/{entry_id}", response_model=ServiceAccountLicenseTypeResponse)
async def get_license_type(
    entry_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
) -> ServiceAccountLicenseTypeResponse:
    """Get a single service account license type by ID.

    Requires licenses.view permission.
    """
    entry = await service.get_license_type_by_id(entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License type entry not found",
        )
    return entry


@router.post("/license-types", response_model=ServiceAccountLicenseTypeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_license_type(
    request: Request,
    data: ServiceAccountLicenseTypeCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> ServiceAccountLicenseTypeResponse:
    """Create a new service account license type.

    Requires licenses.edit permission.
    """
    # Check if license type already exists
    existing_entries = await service.get_all_license_types()
    if any(e.license_type.lower() == data.license_type.lower() for e in existing_entries.items):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A license type rule with this value already exists",
        )

    return await service.create_license_type(
        data=data,
        created_by=current_user.id,
        request=request,
    )


@router.delete("/license-types/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_license_type(
    request: Request,
    entry_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> None:
    """Delete a service account license type.

    Requires licenses.delete permission.
    Note: This does not unmark existing licenses that were marked by this license type.
    """
    # Get entry before deletion for audit
    entry = await service.get_license_type_by_id(entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License type entry not found",
        )

    await service.delete_license_type(
        entry_id=entry_id,
        admin_user_id=current_user.id,
        request=request,
        entry_info={
            "license_type": entry.license_type,
            "name": entry.name,
        },
    )


@router.post("/apply-license-types", response_model=ApplyLicenseTypesResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def apply_license_types(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[ServiceAccountService, Depends(get_service_account_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> ApplyLicenseTypesResponse:
    """Apply all license type rules to all licenses.

    This will mark any licenses with matching license types as service accounts.
    Only updates licenses not already marked as service accounts.

    Requires licenses.edit permission.
    """
    result = await service.apply_license_types_to_all_licenses(
        admin_user_id=current_user.id,
        request=request,
    )

    # Invalidate dashboard cache
    cache = await get_cache_service()
    await cache.invalidate_dashboard()

    return result
