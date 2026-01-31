"""License packages router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.license_package import (
    LicensePackageCreate,
    LicensePackageListResponse,
    LicensePackageResponse,
    LicensePackageUpdate,
)
from licence_api.models.orm.license_package import LicensePackageORM
from licence_api.repositories.license_package_repository import LicensePackageRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.security.auth import require_permission, Permissions

router = APIRouter()


# Dependency injection functions
def get_license_package_repository(
    db: AsyncSession = Depends(get_db),
) -> LicensePackageRepository:
    """Get LicensePackageRepository instance."""
    return LicensePackageRepository(db)


def get_provider_repository(db: AsyncSession = Depends(get_db)) -> ProviderRepository:
    """Get ProviderRepository instance."""
    return ProviderRepository(db)


def _build_package_response(
    package: LicensePackageORM,
    assigned_seats: int,
) -> LicensePackageResponse:
    """Build license package response with utilization stats."""
    available_seats = max(0, package.total_seats - assigned_seats)
    utilization = (assigned_seats / package.total_seats * 100) if package.total_seats > 0 else 0
    total_cost = (
        package.cost_per_seat * package.total_seats
        if package.cost_per_seat
        else None
    )

    return LicensePackageResponse(
        id=package.id,
        provider_id=package.provider_id,
        license_type=package.license_type,
        display_name=package.display_name,
        total_seats=package.total_seats,
        assigned_seats=assigned_seats,
        available_seats=available_seats,
        utilization_percent=round(utilization, 1),
        cost_per_seat=package.cost_per_seat,
        total_monthly_cost=total_cost,
        billing_cycle=package.billing_cycle,
        payment_frequency=package.payment_frequency,
        currency=package.currency,
        contract_start=package.contract_start,
        contract_end=package.contract_end,
        auto_renew=package.auto_renew,
        notes=package.notes,
        created_at=package.created_at,
        updated_at=package.updated_at,
    )


@router.get("/{provider_id}/packages", response_model=LicensePackageListResponse)
async def list_license_packages(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    package_repo: Annotated[LicensePackageRepository, Depends(get_license_package_repository)],
) -> LicensePackageListResponse:
    """List all license packages for a provider."""
    provider = await provider_repo.get(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    packages = await package_repo.get_by_provider(provider_id)
    assigned_counts = await package_repo.get_all_assigned_seats_counts(provider_id)

    items = [
        _build_package_response(p, assigned_counts.get(p.license_type, 0))
        for p in packages
    ]

    return LicensePackageListResponse(items=items, total=len(items))


@router.post("/{provider_id}/packages", response_model=LicensePackageResponse)
async def create_license_package(
    provider_id: UUID,
    data: LicensePackageCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    package_repo: Annotated[LicensePackageRepository, Depends(get_license_package_repository)],
) -> LicensePackageResponse:
    """Create a new license package."""
    provider = await provider_repo.get(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Check if package already exists for this type
    existing = await package_repo.get_by_provider_and_type(provider_id, data.license_type)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"License package for type '{data.license_type}' already exists",
        )

    package = await package_repo.create_package(
        provider_id=provider_id,
        license_type=data.license_type,
        display_name=data.display_name,
        total_seats=data.total_seats,
        cost_per_seat=data.cost_per_seat,
        billing_cycle=data.billing_cycle,
        payment_frequency=data.payment_frequency,
        currency=data.currency,
        contract_start=data.contract_start,
        contract_end=data.contract_end,
        auto_renew=data.auto_renew,
        notes=data.notes,
    )
    await db.commit()

    assigned = await package_repo.get_assigned_seats_count(provider_id, data.license_type)
    return _build_package_response(package, assigned)


@router.put("/{provider_id}/packages/{package_id}", response_model=LicensePackageResponse)
async def update_license_package(
    provider_id: UUID,
    package_id: UUID,
    data: LicensePackageUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    package_repo: Annotated[LicensePackageRepository, Depends(get_license_package_repository)],
) -> LicensePackageResponse:
    """Update a license package."""
    package = await package_repo.get_by_provider_and_id(provider_id, package_id)

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License package not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    package = await package_repo.update_package(package, **update_data)
    await db.commit()

    assigned = await package_repo.get_assigned_seats_count(provider_id, package.license_type)
    return _build_package_response(package, assigned)


@router.delete("/{provider_id}/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_license_package(
    provider_id: UUID,
    package_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    package_repo: Annotated[LicensePackageRepository, Depends(get_license_package_repository)],
) -> None:
    """Delete a license package."""
    package = await package_repo.get_by_provider_and_id(provider_id, package_id)

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License package not found",
        )

    await package_repo.delete_package(package)
    await db.commit()
