"""Organization licenses router."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4

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
from licence_api.models.orm.organization_license import OrganizationLicenseORM
from licence_api.repositories.organization_license_repository import OrganizationLicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.security.auth import require_permission, Permissions

router = APIRouter()


@router.get("/{provider_id}/org-licenses", response_model=OrganizationLicenseListResponse)
async def list_organization_licenses(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationLicenseListResponse:
    """List all organization licenses for a provider."""
    provider_repo = ProviderRepository(db)
    provider = await provider_repo.get(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    repo = OrganizationLicenseRepository(db)
    licenses = await repo.get_by_provider(provider_id)
    total_cost = await repo.get_total_monthly_cost(provider_id)

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
) -> OrganizationLicenseResponse:
    """Create a new organization license."""
    provider_repo = ProviderRepository(db)
    provider = await provider_repo.get(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    license_orm = OrganizationLicenseORM(
        id=uuid4(),
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
    db.add(license_orm)
    await db.commit()
    await db.refresh(license_orm)

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
) -> OrganizationLicenseResponse:
    """Update an organization license."""
    repo = OrganizationLicenseRepository(db)
    license_orm = await repo.get(license_id)

    if not license_orm or license_orm.provider_id != provider_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization license not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(license_orm, key, value)

    await db.commit()
    await db.refresh(license_orm)

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
) -> None:
    """Delete an organization license."""
    repo = OrganizationLicenseRepository(db)
    license_orm = await repo.get(license_id)

    if not license_orm or license_orm.provider_id != provider_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization license not found",
        )

    await repo.delete(license_id)
    await db.commit()
