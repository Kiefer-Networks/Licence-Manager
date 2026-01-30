"""Manual licenses router for providers without API."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.license import LicenseResponse
from licence_api.security.auth import require_permission, Permissions
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.employee_repository import EmployeeRepository

router = APIRouter()


class ManualLicenseCreate(BaseModel):
    """Request to create a manual license."""

    provider_id: UUID
    license_type: str | None = None
    license_key: str | None = None  # Optional license key
    quantity: int = 1  # Number of licenses to create
    monthly_cost: Decimal | None = None
    currency: str = "EUR"
    valid_until: datetime | None = None
    notes: str | None = None
    employee_id: UUID | None = None  # Optional: directly assign to employee


class ManualLicenseUpdate(BaseModel):
    """Request to update a manual license."""

    license_type: str | None = None
    license_key: str | None = None
    monthly_cost: Decimal | None = None
    currency: str | None = None
    valid_until: datetime | None = None
    notes: str | None = None
    employee_id: UUID | None = None  # Assign/unassign


class ManualLicenseBulkCreate(BaseModel):
    """Request to create multiple manual licenses with keys."""

    provider_id: UUID
    license_type: str | None = None
    license_keys: list[str]  # List of license keys
    monthly_cost: Decimal | None = None
    currency: str = "EUR"
    valid_until: datetime | None = None
    notes: str | None = None


@router.post("", response_model=list[LicenseResponse])
async def create_manual_licenses(
    request: ManualLicenseCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_CREATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[LicenseResponse]:
    """Create one or more manual licenses. Requires licenses.create permission."""
    provider_repo = ProviderRepository(db)
    license_repo = LicenseRepository(db)

    # Verify provider exists and is manual type
    provider = await provider_repo.get_by_id(request.provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Check if provider is manual type (stored in config)
    provider_config = provider.config or {}
    if provider_config.get("provider_type") != "manual":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add manual licenses to manual providers",
        )

    created_licenses = []
    now = datetime.now(timezone.utc)

    for i in range(request.quantity):
        # Generate external_user_id for manual licenses
        if request.license_key and request.quantity == 1:
            external_id = request.license_key
        else:
            # Generate unique ID for seat-based or multiple licenses
            external_id = f"manual-{uuid4().hex[:12]}"

        metadata = {
            "manual_entry": True,
            "created_by": str(current_user.id) if current_user.id else "admin",
        }
        if request.license_key and request.quantity == 1:
            metadata["license_key"] = request.license_key
        if request.valid_until:
            metadata["valid_until"] = request.valid_until.isoformat()
        if request.notes:
            metadata["notes"] = request.notes

        license_orm = await license_repo.create(
            provider_id=request.provider_id,
            employee_id=request.employee_id,
            external_user_id=external_id,
            license_type=request.license_type,
            status="active" if request.employee_id else "unassigned",
            assigned_at=now if request.employee_id else None,
            last_activity_at=None,
            monthly_cost=request.monthly_cost,
            currency=request.currency,
            extra_data=metadata,
            synced_at=now,
        )

        # Build response
        employee = None
        if license_orm.employee_id:
            employee_repo = EmployeeRepository(db)
            employee = await employee_repo.get_by_id(license_orm.employee_id)

        created_licenses.append(
            LicenseResponse(
                id=license_orm.id,
                provider_id=license_orm.provider_id,
                provider_name=provider.display_name,
                employee_id=license_orm.employee_id,
                employee_email=employee.email if employee else None,
                employee_name=employee.full_name if employee else None,
                external_user_id=license_orm.external_user_id,
                license_type=license_orm.license_type,
                status=license_orm.status,
                assigned_at=license_orm.assigned_at,
                last_activity_at=license_orm.last_activity_at,
                monthly_cost=license_orm.monthly_cost,
                currency=license_orm.currency,
                metadata=license_orm.extra_data or {},
                synced_at=license_orm.synced_at,
            )
        )

    await db.commit()
    return created_licenses


@router.post("/bulk", response_model=list[LicenseResponse])
async def create_manual_licenses_bulk(
    request: ManualLicenseBulkCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_CREATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[LicenseResponse]:
    """Create multiple manual licenses with individual keys. Requires licenses.create permission."""
    provider_repo = ProviderRepository(db)
    license_repo = LicenseRepository(db)

    # Verify provider exists and is manual type
    provider = await provider_repo.get_by_id(request.provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    provider_config = provider.config or {}
    if provider_config.get("provider_type") != "manual":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add manual licenses to manual providers",
        )

    if len(request.license_keys) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 licenses per bulk operation",
        )

    created_licenses = []
    now = datetime.now(timezone.utc)

    for license_key in request.license_keys:
        metadata = {
            "manual_entry": True,
            "license_key": license_key,
            "created_by": str(current_user.id) if current_user.id else "admin",
        }
        if request.valid_until:
            metadata["valid_until"] = request.valid_until.isoformat()
        if request.notes:
            metadata["notes"] = request.notes

        license_orm = await license_repo.create(
            provider_id=request.provider_id,
            employee_id=None,
            external_user_id=license_key,  # Use key as external ID
            license_type=request.license_type,
            status="unassigned",
            assigned_at=None,
            last_activity_at=None,
            monthly_cost=request.monthly_cost,
            currency=request.currency,
            extra_data=metadata,
            synced_at=now,
        )

        created_licenses.append(
            LicenseResponse(
                id=license_orm.id,
                provider_id=license_orm.provider_id,
                provider_name=provider.display_name,
                employee_id=None,
                employee_email=None,
                employee_name=None,
                external_user_id=license_orm.external_user_id,
                license_type=license_orm.license_type,
                status=license_orm.status,
                assigned_at=None,
                last_activity_at=None,
                monthly_cost=license_orm.monthly_cost,
                currency=license_orm.currency,
                metadata=license_orm.extra_data or {},
                synced_at=license_orm.synced_at,
            )
        )

    await db.commit()
    return created_licenses


@router.put("/{license_id}", response_model=LicenseResponse)
async def update_manual_license(
    license_id: UUID,
    request: ManualLicenseUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseResponse:
    """Update a manual license. Requires licenses.edit permission."""
    license_repo = LicenseRepository(db)
    provider_repo = ProviderRepository(db)
    employee_repo = EmployeeRepository(db)

    # Get license
    license_orm = await license_repo.get_by_id(license_id)
    if not license_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    # Verify it's a manual license
    metadata = license_orm.extra_data or {}
    if not metadata.get("manual_entry"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update manual licenses",
        )

    # Update fields
    update_data = {}

    if request.license_type is not None:
        update_data["license_type"] = request.license_type

    if request.monthly_cost is not None:
        update_data["monthly_cost"] = request.monthly_cost

    if request.currency is not None:
        update_data["currency"] = request.currency

    if request.employee_id is not None:
        update_data["employee_id"] = request.employee_id
        update_data["status"] = "active"
        update_data["assigned_at"] = datetime.now(timezone.utc)
    elif request.employee_id is None and "employee_id" in request.model_fields_set:
        # Explicitly unassign
        update_data["employee_id"] = None
        update_data["status"] = "unassigned"
        update_data["assigned_at"] = None

    # Update metadata
    if request.license_key is not None:
        metadata["license_key"] = request.license_key
    if request.valid_until is not None:
        metadata["valid_until"] = request.valid_until.isoformat()
    if request.notes is not None:
        metadata["notes"] = request.notes

    update_data["extra_data"] = metadata

    # Apply updates
    license_orm = await license_repo.update(license_id, **update_data)
    await db.commit()

    # Get provider and employee for response
    provider = await provider_repo.get_by_id(license_orm.provider_id)
    employee = None
    if license_orm.employee_id:
        employee = await employee_repo.get_by_id(license_orm.employee_id)

    return LicenseResponse(
        id=license_orm.id,
        provider_id=license_orm.provider_id,
        provider_name=provider.display_name if provider else "Unknown",
        employee_id=license_orm.employee_id,
        employee_email=employee.email if employee else None,
        employee_name=employee.full_name if employee else None,
        external_user_id=license_orm.external_user_id,
        license_type=license_orm.license_type,
        status=license_orm.status,
        assigned_at=license_orm.assigned_at,
        last_activity_at=license_orm.last_activity_at,
        monthly_cost=license_orm.monthly_cost,
        currency=license_orm.currency,
        metadata=license_orm.extra_data or {},
        synced_at=license_orm.synced_at,
    )


@router.post("/{license_id}/assign", response_model=LicenseResponse)
async def assign_manual_license(
    license_id: UUID,
    employee_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseResponse:
    """Assign a manual license to an employee. Requires licenses.assign permission."""
    request = ManualLicenseUpdate(employee_id=employee_id)
    return await update_manual_license(license_id, request, current_user, db)


@router.post("/{license_id}/unassign", response_model=LicenseResponse)
async def unassign_manual_license(
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseResponse:
    """Unassign a manual license from an employee. Requires licenses.assign permission."""
    license_repo = LicenseRepository(db)
    provider_repo = ProviderRepository(db)

    # Get license
    license_orm = await license_repo.get_by_id(license_id)
    if not license_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    # Update
    license_orm = await license_repo.update(
        license_id,
        employee_id=None,
        status="unassigned",
        assigned_at=None,
    )
    await db.commit()

    provider = await provider_repo.get_by_id(license_orm.provider_id)

    return LicenseResponse(
        id=license_orm.id,
        provider_id=license_orm.provider_id,
        provider_name=provider.display_name if provider else "Unknown",
        employee_id=None,
        employee_email=None,
        employee_name=None,
        external_user_id=license_orm.external_user_id,
        license_type=license_orm.license_type,
        status=license_orm.status,
        assigned_at=None,
        last_activity_at=license_orm.last_activity_at,
        monthly_cost=license_orm.monthly_cost,
        currency=license_orm.currency,
        metadata=license_orm.extra_data or {},
        synced_at=license_orm.synced_at,
    )


@router.delete("/{license_id}")
async def delete_manual_license(
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Delete a manual license. Requires licenses.delete permission."""
    license_repo = LicenseRepository(db)

    # Get license
    license_orm = await license_repo.get_by_id(license_id)
    if not license_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    # Verify it's a manual license
    metadata = license_orm.extra_data or {}
    if not metadata.get("manual_entry"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete manual licenses",
        )

    await license_repo.delete(license_id)
    await db.commit()

    return {"success": True, "message": "License deleted"}
