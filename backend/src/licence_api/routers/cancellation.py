"""Cancellation and renewal router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from licence_api.dependencies import get_cancellation_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.cancellation import (
    CancellationRequest,
    CancellationResponse,
    NeedsReorderResponse,
    NeedsReorderUpdate,
    RenewRequest,
    RenewalResponse,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.cancellation_service import CancellationService
from licence_api.utils.errors import raise_not_found

router = APIRouter()


# ==================== LICENSE CANCELLATION ====================


@router.post("/licenses/{license_id}/cancel", response_model=CancellationResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def cancel_license(
    request: Request,
    license_id: UUID,
    body: CancellationRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> CancellationResponse:
    """Cancel a license.

    Sets cancellation date and reason. The license status will change to 'cancelled'
    when the effective date is reached.
    """
    try:
        return await service.cancel_license(
            license_id=license_id,
            effective_date=body.effective_date,
            reason=body.reason,
            cancelled_by=current_user.id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("License")


@router.post("/licenses/{license_id}/renew", response_model=RenewalResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def renew_license(
    request: Request,
    license_id: UUID,
    body: RenewRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> RenewalResponse:
    """Renew a license by setting a new expiration date.

    Optionally clears any pending cancellation.
    """
    try:
        return await service.renew_license(
            license_id=license_id,
            new_expiration_date=body.new_expiration_date,
            renewed_by=current_user.id,
            clear_cancellation=body.clear_cancellation,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("License")


@router.patch("/licenses/{license_id}/needs-reorder", response_model=NeedsReorderResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def set_license_needs_reorder(
    request: Request,
    license_id: UUID,
    body: NeedsReorderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> NeedsReorderResponse:
    """Set the needs_reorder flag for a license."""
    try:
        return await service.set_license_needs_reorder(
            license_id=license_id,
            needs_reorder=body.needs_reorder,
            current_user_id=current_user.id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("License")


# ==================== PACKAGE CANCELLATION ====================


@router.post("/packages/{package_id}/cancel", response_model=CancellationResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def cancel_package(
    request: Request,
    package_id: UUID,
    body: CancellationRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> CancellationResponse:
    """Cancel a license package.

    Sets cancellation date and reason. The package status will change to 'cancelled'
    when the effective date is reached.
    """
    try:
        return await service.cancel_package(
            package_id=package_id,
            effective_date=body.effective_date,
            reason=body.reason,
            cancelled_by=current_user.id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("Package")


@router.post("/packages/{package_id}/renew", response_model=RenewalResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def renew_package(
    request: Request,
    package_id: UUID,
    body: RenewRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> RenewalResponse:
    """Renew a license package by setting a new contract end date.

    Optionally clears any pending cancellation.
    """
    try:
        return await service.renew_package(
            package_id=package_id,
            new_contract_end=body.new_expiration_date,
            renewed_by=current_user.id,
            clear_cancellation=body.clear_cancellation,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("Package")


@router.patch("/packages/{package_id}/needs-reorder", response_model=NeedsReorderResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def set_package_needs_reorder(
    request: Request,
    package_id: UUID,
    body: NeedsReorderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> NeedsReorderResponse:
    """Set the needs_reorder flag for a package."""
    try:
        return await service.set_package_needs_reorder(
            package_id=package_id,
            needs_reorder=body.needs_reorder,
            current_user_id=current_user.id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("Package")


# ==================== ORGANIZATION LICENSE CANCELLATION ====================


@router.post("/org-licenses/{org_license_id}/cancel", response_model=CancellationResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def cancel_org_license(
    request: Request,
    org_license_id: UUID,
    body: CancellationRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> CancellationResponse:
    """Cancel an organization license.

    Sets cancellation date and reason. The license status will change to 'cancelled'
    when the effective date is reached.
    """
    try:
        return await service.cancel_org_license(
            org_license_id=org_license_id,
            effective_date=body.effective_date,
            reason=body.reason,
            cancelled_by=current_user.id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("Organization license")


@router.post("/org-licenses/{org_license_id}/renew", response_model=RenewalResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def renew_org_license(
    request: Request,
    org_license_id: UUID,
    body: RenewRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> RenewalResponse:
    """Renew an organization license by setting new renewal/expiration dates.

    Optionally clears any pending cancellation.
    """
    try:
        return await service.renew_org_license(
            org_license_id=org_license_id,
            renewed_by=current_user.id,
            new_renewal_date=body.new_expiration_date,
            new_expires_at=body.new_expiration_date,
            clear_cancellation=body.clear_cancellation,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("Organization license")


@router.patch("/org-licenses/{org_license_id}/needs-reorder", response_model=NeedsReorderResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def set_org_license_needs_reorder(
    request: Request,
    org_license_id: UUID,
    body: NeedsReorderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
) -> NeedsReorderResponse:
    """Set the needs_reorder flag for an organization license."""
    try:
        return await service.set_org_license_needs_reorder(
            org_license_id=org_license_id,
            needs_reorder=body.needs_reorder,
            current_user_id=current_user.id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("Organization license")
