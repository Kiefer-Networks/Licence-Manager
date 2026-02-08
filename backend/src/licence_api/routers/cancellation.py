"""Cancellation and renewal router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from licence_api.dependencies import get_audit_service, get_cancellation_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.cancellation import (
    CancellationRequest,
    CancellationResponse,
    NeedsReorderUpdate,
    RenewRequest,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
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
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> CancellationResponse:
    """Cancel a license.

    Sets cancellation date and reason. The license status will change to 'cancelled'
    when the effective date is reached.
    """
    try:
        license_orm = await service.cancel_license(
            license_id=license_id,
            effective_date=body.effective_date,
            reason=body.reason,
            cancelled_by=current_user.id,
        )
        await audit_service.log(
            action=AuditAction.LICENSE_CANCEL,
            resource_type=ResourceType.LICENSE,
            resource_id=license_id,
            user=current_user,
            request=request,
            details={
                "effective_date": body.effective_date.isoformat() if body.effective_date else None,
                "reason": body.reason,
            },
        )
        return CancellationResponse(
            id=license_orm.id,
            cancelled_at=license_orm.cancelled_at,
            cancellation_effective_date=license_orm.cancellation_effective_date,
            cancellation_reason=license_orm.cancellation_reason,
            cancelled_by=license_orm.cancelled_by,
        )
    except ValueError:
        raise_not_found("License")


@router.post("/licenses/{license_id}/renew")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def renew_license(
    request: Request,
    license_id: UUID,
    body: RenewRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> dict:
    """Renew a license by setting a new expiration date.

    Optionally clears any pending cancellation.
    """
    try:
        license_orm = await service.renew_license(
            license_id=license_id,
            new_expiration_date=body.new_expiration_date,
            renewed_by=current_user.id,
            clear_cancellation=body.clear_cancellation,
        )
        await audit_service.log(
            action=AuditAction.LICENSE_RENEW,
            resource_type=ResourceType.LICENSE,
            resource_id=license_id,
            user=current_user,
            request=request,
            details={
                "new_expiration_date": body.new_expiration_date.isoformat(),
                "clear_cancellation": body.clear_cancellation,
            },
        )
        return {
            "success": True,
            "message": "License renewed successfully",
            "expires_at": license_orm.expires_at.isoformat() if license_orm.expires_at else None,
            "status": license_orm.status,
        }
    except ValueError:
        raise_not_found("License")


@router.patch("/licenses/{license_id}/needs-reorder")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def set_license_needs_reorder(
    request: Request,
    license_id: UUID,
    body: NeedsReorderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> dict:
    """Set the needs_reorder flag for a license."""
    try:
        license_orm = await service.set_license_needs_reorder(
            license_id=license_id,
            needs_reorder=body.needs_reorder,
            flagged_by=current_user.id if body.needs_reorder else None,
        )
        await audit_service.log(
            action=AuditAction.LICENSE_NEEDS_REORDER,
            resource_type=ResourceType.LICENSE,
            resource_id=license_id,
            user=current_user,
            request=request,
            details={"needs_reorder": body.needs_reorder},
        )
        return {
            "success": True,
            "needs_reorder": license_orm.needs_reorder,
        }
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
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> CancellationResponse:
    """Cancel a license package.

    Sets cancellation date and reason. The package status will change to 'cancelled'
    when the effective date is reached.
    """
    try:
        package = await service.cancel_package(
            package_id=package_id,
            effective_date=body.effective_date,
            reason=body.reason,
            cancelled_by=current_user.id,
        )
        await audit_service.log(
            action=AuditAction.PACKAGE_CANCEL,
            resource_type=ResourceType.LICENSE_PACKAGE,
            resource_id=package_id,
            user=current_user,
            request=request,
            details={
                "effective_date": body.effective_date.isoformat() if body.effective_date else None,
                "reason": body.reason,
            },
        )
        return CancellationResponse(
            id=package.id,
            cancelled_at=package.cancelled_at,
            cancellation_effective_date=package.cancellation_effective_date,
            cancellation_reason=package.cancellation_reason,
            cancelled_by=package.cancelled_by,
        )
    except ValueError:
        raise_not_found("Package")


@router.post("/packages/{package_id}/renew")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def renew_package(
    request: Request,
    package_id: UUID,
    body: RenewRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> dict:
    """Renew a license package by setting a new contract end date.

    Optionally clears any pending cancellation.
    """
    try:
        package = await service.renew_package(
            package_id=package_id,
            new_contract_end=body.new_expiration_date,
            renewed_by=current_user.id,
            clear_cancellation=body.clear_cancellation,
        )
        await audit_service.log(
            action=AuditAction.PACKAGE_RENEW,
            resource_type=ResourceType.LICENSE_PACKAGE,
            resource_id=package_id,
            user=current_user,
            request=request,
            details={
                "new_contract_end": body.new_expiration_date.isoformat(),
                "clear_cancellation": body.clear_cancellation,
            },
        )
        return {
            "success": True,
            "message": "Package renewed successfully",
            "contract_end": package.contract_end.isoformat() if package.contract_end else None,
            "status": package.status,
        }
    except ValueError:
        raise_not_found("Package")


@router.patch("/packages/{package_id}/needs-reorder")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def set_package_needs_reorder(
    request: Request,
    package_id: UUID,
    body: NeedsReorderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> dict:
    """Set the needs_reorder flag for a package."""
    try:
        package = await service.set_package_needs_reorder(
            package_id=package_id,
            needs_reorder=body.needs_reorder,
            flagged_by=current_user.id if body.needs_reorder else None,
        )
        await audit_service.log(
            action=AuditAction.PACKAGE_NEEDS_REORDER,
            resource_type=ResourceType.LICENSE_PACKAGE,
            resource_id=package_id,
            user=current_user,
            request=request,
            details={"needs_reorder": body.needs_reorder},
        )
        return {
            "success": True,
            "needs_reorder": package.needs_reorder,
        }
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
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> CancellationResponse:
    """Cancel an organization license.

    Sets cancellation date and reason. The license status will change to 'cancelled'
    when the effective date is reached.
    """
    try:
        org_license = await service.cancel_org_license(
            org_license_id=org_license_id,
            effective_date=body.effective_date,
            reason=body.reason,
            cancelled_by=current_user.id,
        )
        await audit_service.log(
            action=AuditAction.ORG_LICENSE_CANCEL,
            resource_type=ResourceType.ORG_LICENSE,
            resource_id=org_license_id,
            user=current_user,
            request=request,
            details={
                "effective_date": body.effective_date.isoformat() if body.effective_date else None,
                "reason": body.reason,
            },
        )
        return CancellationResponse(
            id=org_license.id,
            cancelled_at=org_license.cancelled_at,
            cancellation_effective_date=org_license.cancellation_effective_date,
            cancellation_reason=org_license.cancellation_reason,
            cancelled_by=org_license.cancelled_by,
        )
    except ValueError:
        raise_not_found("Organization license")


@router.post("/org-licenses/{org_license_id}/renew")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def renew_org_license(
    request: Request,
    org_license_id: UUID,
    body: RenewRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> dict:
    """Renew an organization license by setting new renewal/expiration dates.

    Optionally clears any pending cancellation.
    """
    try:
        org_license = await service.renew_org_license(
            org_license_id=org_license_id,
            renewed_by=current_user.id,
            new_renewal_date=body.new_expiration_date,
            new_expires_at=body.new_expiration_date,
            clear_cancellation=body.clear_cancellation,
        )
        await audit_service.log(
            action=AuditAction.ORG_LICENSE_RENEW,
            resource_type=ResourceType.ORG_LICENSE,
            resource_id=org_license_id,
            user=current_user,
            request=request,
            details={
                "new_expiration_date": body.new_expiration_date.isoformat(),
                "clear_cancellation": body.clear_cancellation,
            },
        )
        return {
            "success": True,
            "message": "Organization license renewed successfully",
            "renewal_date": org_license.renewal_date.isoformat()
            if org_license.renewal_date
            else None,
            "expires_at": org_license.expires_at.isoformat() if org_license.expires_at else None,
            "status": org_license.status,
        }
    except ValueError:
        raise_not_found("Organization license")


@router.patch("/org-licenses/{org_license_id}/needs-reorder")
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def set_org_license_needs_reorder(
    request: Request,
    org_license_id: UUID,
    body: NeedsReorderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    service: Annotated[CancellationService, Depends(get_cancellation_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> dict:
    """Set the needs_reorder flag for an organization license."""
    try:
        org_license = await service.set_org_license_needs_reorder(
            org_license_id=org_license_id,
            needs_reorder=body.needs_reorder,
            flagged_by=current_user.id if body.needs_reorder else None,
        )
        await audit_service.log(
            action=AuditAction.ORG_LICENSE_NEEDS_REORDER,
            resource_type=ResourceType.ORG_LICENSE,
            resource_id=org_license_id,
            user=current_user,
            request=request,
            details={"needs_reorder": body.needs_reorder},
        )
        return {
            "success": True,
            "needs_reorder": org_license.needs_reorder,
        }
    except ValueError:
        raise_not_found("Organization license")
