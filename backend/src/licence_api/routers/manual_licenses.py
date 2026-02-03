"""Manual licenses router for providers without API."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.license import LicenseResponse
from licence_api.security.auth import require_permission, Permissions
from licence_api.security.csrf import CSRFProtected
from licence_api.security.rate_limit import limiter, SENSITIVE_OPERATION_LIMIT
from licence_api.services.manual_license_service import ManualLicenseService

router = APIRouter()


class ManualLicenseCreate(BaseModel):
    """Request to create a manual license."""

    provider_id: UUID
    license_type: str | None = Field(default=None, max_length=255)
    license_key: str | None = Field(default=None, max_length=500)
    quantity: int = Field(default=1, ge=1, le=1000)
    monthly_cost: Decimal | None = Field(default=None, ge=0, le=1000000)
    currency: str = Field(default="EUR", max_length=3, pattern=r"^[A-Z]{3}$")
    valid_until: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)
    employee_id: UUID | None = None


class ManualLicenseUpdate(BaseModel):
    """Request to update a manual license."""

    license_type: str | None = Field(default=None, max_length=255)
    license_key: str | None = Field(default=None, max_length=500)
    monthly_cost: Decimal | None = Field(default=None, ge=0, le=1000000)
    currency: str | None = Field(default=None, max_length=3, pattern=r"^[A-Z]{3}$")
    valid_until: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)
    employee_id: UUID | None = None


class ManualLicenseBulkCreate(BaseModel):
    """Request to create multiple manual licenses with keys."""

    provider_id: UUID
    license_type: str | None = Field(default=None, max_length=255)
    license_keys: list[str] = Field(max_length=100)  # Max 100 keys
    monthly_cost: Decimal | None = Field(default=None, ge=0, le=1000000)
    currency: str = Field(default="EUR", max_length=3, pattern=r"^[A-Z]{3}$")
    valid_until: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("license_keys")
    @classmethod
    def validate_license_keys(cls, v: list[str]) -> list[str]:
        """Validate each license key has max length."""
        for key in v:
            if len(key) > 500:
                raise ValueError("Each license key must be max 500 characters")
        return v


class AssignLicenseRequest(BaseModel):
    """Request to assign a license to an employee."""

    employee_id: UUID


def get_manual_license_service(db: AsyncSession = Depends(get_db)) -> ManualLicenseService:
    """Get ManualLicenseService instance."""
    return ManualLicenseService(db)


@router.post("", response_model=list[LicenseResponse])
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_manual_licenses(
    request: Request,
    body: ManualLicenseCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_CREATE))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> list[LicenseResponse]:
    """Create one or more manual licenses. Requires licenses.create permission."""
    try:
        return await service.create_licenses(
            provider_id=body.provider_id,
            quantity=body.quantity,
            license_type=body.license_type,
            license_key=body.license_key,
            monthly_cost=body.monthly_cost,
            currency=body.currency,
            valid_until=body.valid_until,
            notes=body.notes,
            employee_id=body.employee_id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid license data or provider not found")


@router.post("/bulk", response_model=list[LicenseResponse])
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_manual_licenses_bulk(
    request: Request,
    body: ManualLicenseBulkCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_CREATE))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> list[LicenseResponse]:
    """Create multiple manual licenses with individual keys. Requires licenses.create permission."""
    try:
        return await service.create_licenses_bulk(
            provider_id=body.provider_id,
            license_keys=body.license_keys,
            license_type=body.license_type,
            monthly_cost=body.monthly_cost,
            currency=body.currency,
            valid_until=body.valid_until,
            notes=body.notes,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid license data or provider not found")


@router.put("/{license_id}", response_model=LicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_manual_license(
    request: Request,
    license_id: UUID,
    body: ManualLicenseUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> LicenseResponse:
    """Update a manual license. Requires licenses.edit permission."""
    try:
        # Determine if we should unassign
        unassign = body.employee_id is None and "employee_id" in body.model_fields_set

        return await service.update_license(
            license_id=license_id,
            license_type=body.license_type,
            license_key=body.license_key,
            monthly_cost=body.monthly_cost,
            currency=body.currency,
            valid_until=body.valid_until,
            notes=body.notes,
            employee_id=body.employee_id if not unassign else None,
            unassign=unassign,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="License not found or invalid update data")


@router.post("/{license_id}/assign", response_model=LicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def assign_manual_license(
    request: Request,
    license_id: UUID,
    body: AssignLicenseRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> LicenseResponse:
    """Assign a manual license to an employee. Requires licenses.assign permission."""
    try:
        return await service.update_license(
            license_id=license_id,
            employee_id=body.employee_id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="License or employee not found")


@router.post("/{license_id}/unassign", response_model=LicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def unassign_manual_license(
    request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> LicenseResponse:
    """Unassign a manual license from an employee. Requires licenses.assign permission."""
    try:
        return await service.unassign_license(
            license_id=license_id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")


@router.delete("/{license_id}")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_manual_license(
    request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    service: Annotated[ManualLicenseService, Depends(get_manual_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> dict:
    """Delete a manual license. Requires licenses.delete permission."""
    try:
        await service.delete_license(
            license_id=license_id,
            user=current_user,
            request=request,
        )
        return {"success": True, "message": "License deleted"}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
