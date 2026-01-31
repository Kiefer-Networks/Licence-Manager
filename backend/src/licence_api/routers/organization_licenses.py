"""Organization licenses router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.organization_license import (
    OrganizationLicenseCreate,
    OrganizationLicenseListResponse,
    OrganizationLicenseResponse,
    OrganizationLicenseUpdate,
)
from licence_api.repositories.organization_license_repository import OrganizationLicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.security.auth import require_permission, Permissions

router = APIRouter()


# Dependency injection functions
def get_organization_license_repository(
    db: AsyncSession = Depends(get_db),
) -> OrganizationLicenseRepository:
    """Get OrganizationLicenseRepository instance."""
    return OrganizationLicenseRepository(db)


def get_provider_repository(db: AsyncSession = Depends(get_db)) -> ProviderRepository:
    """Get ProviderRepository instance."""
    return ProviderRepository(db)


@router.get("/{provider_id}/org-licenses", response_model=OrganizationLicenseListResponse)
async def list_organization_licenses(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    license_repo: Annotated[OrganizationLicenseRepository, Depends(get_organization_license_repository)],
) -> OrganizationLicenseListResponse:
    """List all organization licenses for a provider."""
    provider = await provider_repo.get(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    licenses = await license_repo.get_by_provider(provider_id)
    total_cost = await license_repo.get_total_monthly_cost(provider_id)

    items = [
        OrganizationLicenseResponse(
            id=lic.id,
            provider_id=lic.provider_id,
            name=lic.name,
            license_type=lic.license_type,
            quantity=lic.quantity,
            unit=lic.unit,
            monthly_cost=lic.monthly_cost,
            currency=lic.currency,
            billing_cycle=lic.billing_cycle,
            renewal_date=lic.renewal_date,
            notes=lic.notes,
            created_at=lic.created_at,
            updated_at=lic.updated_at,
        )
        for lic in licenses
    ]

    return OrganizationLicenseListResponse(
        items=items,
        total=len(items),
        total_monthly_cost=total_cost,
    )


@router.post("/{provider_id}/org-licenses", response_model=OrganizationLicenseResponse)
async def create_organization_license(
    provider_id: UUID,
    data: OrganizationLicenseCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    license_repo: Annotated[OrganizationLicenseRepository, Depends(get_organization_license_repository)],
) -> OrganizationLicenseResponse:
    """Create a new organization license."""
    provider = await provider_repo.get(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    license_orm = await license_repo.create_organization_license(
        provider_id=provider_id,
        name=data.name,
        license_type=data.license_type,
        quantity=data.quantity,
        unit=data.unit,
        monthly_cost=data.monthly_cost,
        currency=data.currency,
        billing_cycle=data.billing_cycle,
        renewal_date=data.renewal_date,
        notes=data.notes,
    )
    await db.commit()

    return OrganizationLicenseResponse(
        id=license_orm.id,
        provider_id=license_orm.provider_id,
        name=license_orm.name,
        license_type=license_orm.license_type,
        quantity=license_orm.quantity,
        unit=license_orm.unit,
        monthly_cost=license_orm.monthly_cost,
        currency=license_orm.currency,
        billing_cycle=license_orm.billing_cycle,
        renewal_date=license_orm.renewal_date,
        notes=license_orm.notes,
        created_at=license_orm.created_at,
        updated_at=license_orm.updated_at,
    )


@router.put("/{provider_id}/org-licenses/{license_id}", response_model=OrganizationLicenseResponse)
async def update_organization_license(
    provider_id: UUID,
    license_id: UUID,
    data: OrganizationLicenseUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    license_repo: Annotated[OrganizationLicenseRepository, Depends(get_organization_license_repository)],
) -> OrganizationLicenseResponse:
    """Update an organization license."""
    license_orm = await license_repo.get_by_provider_and_id(provider_id, license_id)

    if not license_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization license not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    license_orm = await license_repo.update_organization_license(license_orm, **update_data)
    await db.commit()

    return OrganizationLicenseResponse(
        id=license_orm.id,
        provider_id=license_orm.provider_id,
        name=license_orm.name,
        license_type=license_orm.license_type,
        quantity=license_orm.quantity,
        unit=license_orm.unit,
        monthly_cost=license_orm.monthly_cost,
        currency=license_orm.currency,
        billing_cycle=license_orm.billing_cycle,
        renewal_date=license_orm.renewal_date,
        notes=license_orm.notes,
        created_at=license_orm.created_at,
        updated_at=license_orm.updated_at,
    )


@router.delete("/{provider_id}/org-licenses/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization_license(
    provider_id: UUID,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    license_repo: Annotated[OrganizationLicenseRepository, Depends(get_organization_license_repository)],
) -> None:
    """Delete an organization license."""
    license_orm = await license_repo.get_by_provider_and_id(provider_id, license_id)

    if not license_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization license not found",
        )

    await license_repo.delete_organization_license(license_orm)
    await db.commit()
