"""License packages router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from licence_api.dependencies import get_license_package_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.license_package import (
    LicensePackageCreate,
    LicensePackageListResponse,
    LicensePackageResponse,
    LicensePackageUpdate,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import EXPENSIVE_READ_LIMIT, SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.license_package_service import LicensePackageService
from licence_api.utils.errors import raise_bad_request, raise_not_found

router = APIRouter()


@router.get("/{provider_id}/packages", response_model=LicensePackageListResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_license_packages(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[LicensePackageService, Depends(get_license_package_service)],
) -> LicensePackageListResponse:
    """List all license packages for a provider."""
    try:
        return await service.list_packages(provider_id)
    except ValueError:
        raise_not_found("Provider")


@router.post("/{provider_id}/packages", response_model=LicensePackageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_license_package(
    request: Request,
    provider_id: UUID,
    data: LicensePackageCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[LicensePackageService, Depends(get_license_package_service)],
) -> LicensePackageResponse:
    """Create a new license package."""
    try:
        return await service.create_package(
            provider_id=provider_id,
            data=data,
            admin_user_id=current_user.id,
            request=request,
        )
    except ValueError:
        raise_bad_request("Invalid package data or provider not found")


@router.put("/{provider_id}/packages/{package_id}", response_model=LicensePackageResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_license_package(
    request: Request,
    provider_id: UUID,
    package_id: UUID,
    data: LicensePackageUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[LicensePackageService, Depends(get_license_package_service)],
) -> LicensePackageResponse:
    """Update a license package."""
    try:
        return await service.update_package(
            provider_id=provider_id,
            package_id=package_id,
            data=data,
            admin_user_id=current_user.id,
            request=request,
        )
    except ValueError:
        raise_not_found("Package or provider")


@router.delete("/{provider_id}/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_license_package(
    request: Request,
    provider_id: UUID,
    package_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    service: Annotated[LicensePackageService, Depends(get_license_package_service)],
) -> None:
    """Delete a license package. Requires licenses.delete permission."""
    try:
        await service.delete_package(
            provider_id=provider_id,
            package_id=package_id,
            admin_user_id=current_user.id,
            request=request,
        )
    except ValueError:
        raise_not_found("Package or provider")
