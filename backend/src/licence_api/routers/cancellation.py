"""Cancellation and renewal router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.cancellation import (
    CancellationRequest,
    CancellationResponse,
    NeedsReorderUpdate,
    RenewRequest,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import limiter, SENSITIVE_OPERATION_LIMIT
from licence_api.services.cancellation_service import CancellationService

router = APIRouter()


def get_cancellation_service(db: AsyncSession = Depends(get_db)) -> CancellationService:
    """Get CancellationService instance."""
    return CancellationService(db)


# ==================== LICENSE CANCELLATION ====================


@router.post("/licenses/{license_id}/cancel", response_model=CancellationResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def cancel_license(
    http_request: Request,
    license_id: UUID,
    request: CancellationRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> CancellationResponse:
    """Cancel a license.

    Sets cancellation date and reason. The license status will change to 'cancelled'
    when the effective date is reached.
    """
    try:
        license_orm = await service.cancel_license(
            license_id=license_id,
            effective_date=request.effective_date,
            reason=request.reason,
            cancelled_by=current_user.id,
        )
        return CancellationResponse(
            id=license_orm.id,
            cancelled_at=license_orm.cancelled_at,
            cancellation_effective_date=license_orm.cancellation_effective_date,
            cancellation_reason=license_orm.cancellation_reason,
            cancelled_by=license_orm.cancelled_by,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="License not found")


@router.post("/licenses/{license_id}/renew")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def renew_license(
    http_request: Request,
    license_id: UUID,
    request: RenewRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> dict:
    """Renew a license by setting a new expiration date.

    Optionally clears any pending cancellation.
    """
    try:
        license_orm = await service.renew_license(
            license_id=license_id,
            new_expiration_date=request.new_expiration_date,
            clear_cancellation=request.clear_cancellation,
        )
        return {
            "success": True,
            "message": "License renewed successfully",
            "expires_at": license_orm.expires_at.isoformat() if license_orm.expires_at else None,
            "status": license_orm.status,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="License not found")


@router.patch("/licenses/{license_id}/needs-reorder")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def set_license_needs_reorder(
    http_request: Request,
    license_id: UUID,
    request: NeedsReorderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> dict:
    """Set the needs_reorder flag for a license."""
    try:
        license_orm = await service.set_license_needs_reorder(
            license_id=license_id,
            needs_reorder=request.needs_reorder,
        )
        return {
            "success": True,
            "needs_reorder": license_orm.needs_reorder,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="License not found")


# ==================== PACKAGE CANCELLATION ====================


@router.post("/packages/{package_id}/cancel", response_model=CancellationResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def cancel_package(
    http_request: Request,
    package_id: UUID,
    request: CancellationRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> CancellationResponse:
    """Cancel a license package.

    Sets cancellation date and reason. The package status will change to 'cancelled'
    when the effective date is reached.
    """
    try:
        package = await service.cancel_package(
            package_id=package_id,
            effective_date=request.effective_date,
            reason=request.reason,
            cancelled_by=current_user.id,
        )
        return CancellationResponse(
            id=package.id,
            cancelled_at=package.cancelled_at,
            cancellation_effective_date=package.cancellation_effective_date,
            cancellation_reason=package.cancellation_reason,
            cancelled_by=package.cancelled_by,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Package not found")


@router.post("/packages/{package_id}/renew")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def renew_package(
    http_request: Request,
    package_id: UUID,
    request: RenewRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> dict:
    """Renew a license package by setting a new contract end date.

    Optionally clears any pending cancellation.
    """
    try:
        package = await service.renew_package(
            package_id=package_id,
            new_contract_end=request.new_expiration_date,
            clear_cancellation=request.clear_cancellation,
        )
        return {
            "success": True,
            "message": "Package renewed successfully",
            "contract_end": package.contract_end.isoformat() if package.contract_end else None,
            "status": package.status,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Package not found")


@router.patch("/packages/{package_id}/needs-reorder")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def set_package_needs_reorder(
    http_request: Request,
    package_id: UUID,
    request: NeedsReorderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> dict:
    """Set the needs_reorder flag for a package."""
    try:
        package = await service.set_package_needs_reorder(
            package_id=package_id,
            needs_reorder=request.needs_reorder,
        )
        return {
            "success": True,
            "needs_reorder": package.needs_reorder,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Package not found")


# ==================== ORGANIZATION LICENSE CANCELLATION ====================


@router.post("/org-licenses/{org_license_id}/cancel", response_model=CancellationResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def cancel_org_license(
    http_request: Request,
    org_license_id: UUID,
    request: CancellationRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> CancellationResponse:
    """Cancel an organization license.

    Sets cancellation date and reason. The license status will change to 'cancelled'
    when the effective date is reached.
    """
    try:
        org_license = await service.cancel_org_license(
            org_license_id=org_license_id,
            effective_date=request.effective_date,
            reason=request.reason,
            cancelled_by=current_user.id,
        )
        return CancellationResponse(
            id=org_license.id,
            cancelled_at=org_license.cancelled_at,
            cancellation_effective_date=org_license.cancellation_effective_date,
            cancellation_reason=org_license.cancellation_reason,
            cancelled_by=org_license.cancelled_by,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Organization license not found")
