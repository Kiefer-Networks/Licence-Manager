"""Manual licenses router for providers without API."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.license import LicenseResponse
from licence_api.security.auth import require_permission, Permissions
from licence_api.services.manual_license_service import ManualLicenseService

router = APIRouter()


class ManualLicenseCreate(BaseModel):
    """Request to create a manual license."""

    provider_id: UUID
    license_type: str | None = None
    license_key: str | None = None
    quantity: int = 1
    monthly_cost: Decimal | None = None
    currency: str = "EUR"
    valid_until: datetime | None = None
    notes: str | None = None
    employee_id: UUID | None = None


class ManualLicenseUpdate(BaseModel):
    """Request to update a manual license."""

    license_type: str | None = None
    license_key: str | None = None
    monthly_cost: Decimal | None = None
    currency: str | None = None
    valid_until: datetime | None = None
    notes: str | None = None
    employee_id: UUID | None = None


class ManualLicenseBulkCreate(BaseModel):
    """Request to create multiple manual licenses with keys."""

    provider_id: UUID
    license_type: str | None = None
    license_keys: list[str]
    monthly_cost: Decimal | None = None
    currency: str = "EUR"
    valid_until: datetime | None = None
    notes: str | None = None


def get_manual_license_service(db: AsyncSession = Depends(get_db)) -> ManualLicenseService:
    """Get ManualLicenseService instance."""
    return ManualLicenseService(db)


@router.post("", response_model=list[LicenseResponse])
async def create_manual_licenses(
    http_request: Request,
    request: ManualLicenseCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_CREATE))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
) -> list[LicenseResponse]:
    """Create one or more manual licenses. Requires licenses.create permission."""
    try:
        return await service.create_licenses(
            provider_id=request.provider_id,
            quantity=request.quantity,
            license_type=request.license_type,
            license_key=request.license_key,
            monthly_cost=request.monthly_cost,
            currency=request.currency,
            valid_until=request.valid_until,
            notes=request.notes,
            employee_id=request.employee_id,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid license data or provider not found")


@router.post("/bulk", response_model=list[LicenseResponse])
async def create_manual_licenses_bulk(
    http_request: Request,
    request: ManualLicenseBulkCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_CREATE))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
) -> list[LicenseResponse]:
    """Create multiple manual licenses with individual keys. Requires licenses.create permission."""
    try:
        return await service.create_licenses_bulk(
            provider_id=request.provider_id,
            license_keys=request.license_keys,
            license_type=request.license_type,
            monthly_cost=request.monthly_cost,
            currency=request.currency,
            valid_until=request.valid_until,
            notes=request.notes,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid license data or provider not found")


@router.put("/{license_id}", response_model=LicenseResponse)
async def update_manual_license(
    http_request: Request,
    license_id: UUID,
    request: ManualLicenseUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
) -> LicenseResponse:
    """Update a manual license. Requires licenses.edit permission."""
    try:
        # Determine if we should unassign
        unassign = request.employee_id is None and "employee_id" in request.model_fields_set

        return await service.update_license(
            license_id=license_id,
            license_type=request.license_type,
            license_key=request.license_key,
            monthly_cost=request.monthly_cost,
            currency=request.currency,
            valid_until=request.valid_until,
            notes=request.notes,
            employee_id=request.employee_id if not unassign else None,
            unassign=unassign,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="License not found or invalid update data")


@router.post("/{license_id}/assign", response_model=LicenseResponse)
async def assign_manual_license(
    http_request: Request,
    license_id: UUID,
    employee_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
) -> LicenseResponse:
    """Assign a manual license to an employee. Requires licenses.assign permission."""
    try:
        return await service.update_license(
            license_id=license_id,
            employee_id=employee_id,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="License or employee not found")


@router.post("/{license_id}/unassign", response_model=LicenseResponse)
async def unassign_manual_license(
    http_request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
) -> LicenseResponse:
    """Unassign a manual license from an employee. Requires licenses.assign permission."""
    try:
        return await service.unassign_license(
            license_id=license_id,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")


@router.delete("/{license_id}")
async def delete_manual_license(
    http_request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
) -> dict:
    """Delete a manual license. Requires licenses.delete permission."""
    try:
        await service.delete_license(
            license_id=license_id,
            user=current_user,
            request=http_request,
        )
        return {"success": True, "message": "License deleted"}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
