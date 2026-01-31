"""Organization licenses router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.organization_license import (
    OrganizationLicenseCreate,
    OrganizationLicenseListResponse,
    OrganizationLicenseResponse,
    OrganizationLicenseUpdate,
)
from licence_api.security.auth import require_permission, Permissions
from licence_api.services.organization_license_service import OrganizationLicenseService

router = APIRouter()


def get_organization_license_service(
    db: AsyncSession = Depends(get_db),
) -> OrganizationLicenseService:
    """Get OrganizationLicenseService instance."""
    return OrganizationLicenseService(db)


@router.get("/{provider_id}/org-licenses", response_model=OrganizationLicenseListResponse)
async def list_organization_licenses(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[OrganizationLicenseService, Depends(get_organization_license_service)],
) -> OrganizationLicenseListResponse:
    """List all organization licenses for a provider."""
    try:
        return await service.list_licenses(provider_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{provider_id}/org-licenses", response_model=OrganizationLicenseResponse)
async def create_organization_license(
    provider_id: UUID,
    data: OrganizationLicenseCreate,
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[OrganizationLicenseService, Depends(get_organization_license_service)],
) -> OrganizationLicenseResponse:
    """Create a new organization license."""
    try:
        return await service.create_license(
            provider_id=provider_id,
            data=data,
            admin_user_id=current_user.id,
            request=request,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{provider_id}/org-licenses/{license_id}", response_model=OrganizationLicenseResponse)
async def update_organization_license(
    provider_id: UUID,
    license_id: UUID,
    data: OrganizationLicenseUpdate,
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[OrganizationLicenseService, Depends(get_organization_license_service)],
) -> OrganizationLicenseResponse:
    """Update an organization license."""
    try:
        return await service.update_license(
            provider_id=provider_id,
            license_id=license_id,
            data=data,
            admin_user_id=current_user.id,
            request=request,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{provider_id}/org-licenses/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization_license(
    provider_id: UUID,
    license_id: UUID,
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[OrganizationLicenseService, Depends(get_organization_license_service)],
) -> None:
    """Delete an organization license."""
    try:
        await service.delete_license(
            provider_id=provider_id,
            license_id=license_id,
            admin_user_id=current_user.id,
            request=request,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
