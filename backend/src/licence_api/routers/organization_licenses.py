"""Organization licenses router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.organization_license import (
    OrganizationLicenseCreate,
    OrganizationLicenseListResponse,
    OrganizationLicenseResponse,
    OrganizationLicenseUpdate,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.organization_license_service import OrganizationLicenseService
from licence_api.utils.errors import raise_not_found

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
    except ValueError:
        raise_not_found("Provider")


@router.post("/{provider_id}/org-licenses", response_model=OrganizationLicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_organization_license(
    request: Request,
    provider_id: UUID,
    data: OrganizationLicenseCreate,
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
    except ValueError:
        raise_not_found("Provider")


@router.put("/{provider_id}/org-licenses/{license_id}", response_model=OrganizationLicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_organization_license(
    request: Request,
    provider_id: UUID,
    license_id: UUID,
    data: OrganizationLicenseUpdate,
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
    except ValueError:
        raise_not_found("License or provider")


@router.delete("/{provider_id}/org-licenses/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_organization_license(
    request: Request,
    provider_id: UUID,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    service: Annotated[OrganizationLicenseService, Depends(get_organization_license_service)],
) -> None:
    """Delete an organization license. Requires licenses.delete permission."""
    try:
        await service.delete_license(
            provider_id=provider_id,
            license_id=license_id,
            admin_user_id=current_user.id,
            request=request,
        )
    except ValueError:
        raise_not_found("License or provider")
