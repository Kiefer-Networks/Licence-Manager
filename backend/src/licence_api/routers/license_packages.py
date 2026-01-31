"""License packages router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.license_package import (
    LicensePackageCreate,
    LicensePackageListResponse,
    LicensePackageResponse,
    LicensePackageUpdate,
)
from licence_api.security.auth import require_permission, Permissions
from licence_api.services.license_package_service import LicensePackageService

router = APIRouter()


def get_license_package_service(
    db: AsyncSession = Depends(get_db),
) -> LicensePackageService:
    """Get LicensePackageService instance."""
    return LicensePackageService(db)


@router.get("/{provider_id}/packages", response_model=LicensePackageListResponse)
async def list_license_packages(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[LicensePackageService, Depends(get_license_package_service)],
) -> LicensePackageListResponse:
    """List all license packages for a provider."""
    try:
        return await service.list_packages(provider_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{provider_id}/packages", response_model=LicensePackageResponse)
async def create_license_package(
    provider_id: UUID,
    data: LicensePackageCreate,
    request: Request,
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
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        elif "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )


@router.put("/{provider_id}/packages/{package_id}", response_model=LicensePackageResponse)
async def update_license_package(
    provider_id: UUID,
    package_id: UUID,
    data: LicensePackageUpdate,
    request: Request,
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{provider_id}/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_license_package(
    provider_id: UUID,
    package_id: UUID,
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[LicensePackageService, Depends(get_license_package_service)],
) -> None:
    """Delete a license package."""
    try:
        await service.delete_package(
            provider_id=provider_id,
            package_id=package_id,
            admin_user_id=current_user.id,
            request=request,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
