"""Licenses router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.license import (
    AdminAccountUpdate,
    CategorizedLicensesResponse,
    LicenseListResponse,
    LicenseResponse,
    LicenseTypeUpdate,
    ServiceAccountUpdate,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.csrf import CSRFProtected
from licence_api.security.rate_limit import SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.license_service import LicenseService
from licence_api.services.matching_service import MatchingService
from licence_api.utils.validation import (
    sanitize_department,
    sanitize_search,
    sanitize_status,
    validate_sort_by,
)

router = APIRouter()


# Dependency injection functions
def get_license_service(db: AsyncSession = Depends(get_db)) -> LicenseService:
    """Get LicenseService instance."""
    return LicenseService(db)


def get_matching_service(db: AsyncSession = Depends(get_db)) -> MatchingService:
    """Get MatchingService instance."""
    return MatchingService(db)


class AssignLicenseRequest(BaseModel):
    """Request to assign a license to an employee."""

    employee_id: UUID


class RemoveMemberResponse(BaseModel):
    """Response from remove member operation."""

    success: bool
    message: str


class BulkActionRequest(BaseModel):
    """Request for bulk license actions."""

    license_ids: list[UUID] = Field(max_length=500)


class BulkActionResult(BaseModel):
    """Result of a single bulk action."""

    license_id: str
    success: bool
    message: str


class BulkActionResponse(BaseModel):
    """Response from bulk action operation."""

    total: int
    successful: int
    failed: int
    results: list[BulkActionResult]


class ManualAssignRequest(BaseModel):
    """Request to manually assign a license to an employee."""

    employee_id: UUID


class MatchActionResponse(BaseModel):
    """Response from match action operations."""

    success: bool
    message: str
    license: LicenseResponse | None = None


# Allowed status values for licenses
ALLOWED_LICENSE_STATUSES = {"active", "inactive", "suspended", "pending"}

# Allowed sort columns for licenses (whitelist to prevent injection)
ALLOWED_LICENSE_SORT_COLUMNS = {
    "external_user_id",
    "synced_at",
    "status",
    "created_at",
    "employee_name",
    "provider_name",
    "is_external",
}


@router.get("", response_model=LicenseListResponse)
async def list_licenses(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    provider_id: UUID | None = None,
    employee_id: UUID | None = None,
    status: str | None = None,
    unassigned: bool = False,
    external: bool = False,
    search: str | None = Query(default=None, max_length=200),
    department: str | None = Query(
        default=None, max_length=100, description="Filter by employee department"
    ),
    sort_by: str = Query(default="synced_at", max_length=50),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=50, ge=1, le=200),
) -> LicenseListResponse:
    """List licenses with optional filters. Requires licenses.view permission."""
    # Sanitize inputs for defense in depth
    sanitized_search = sanitize_search(search)
    sanitized_department = sanitize_department(department)
    sanitized_status = sanitize_status(status, ALLOWED_LICENSE_STATUSES)
    validated_sort_by = validate_sort_by(sort_by, ALLOWED_LICENSE_SORT_COLUMNS, "synced_at")

    return await license_service.list_licenses(
        provider_id=provider_id,
        employee_id=employee_id,
        status=sanitized_status,
        unassigned_only=unassigned,
        external_only=external,
        search=sanitized_search,
        department=sanitized_department,
        sort_by=validated_sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.get("/categorized", response_model=CategorizedLicensesResponse)
async def get_categorized_licenses(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    provider_id: UUID | None = None,
    sort_by: str = Query(default="external_user_id", max_length=50),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> CategorizedLicensesResponse:
    """Get licenses categorized into assigned, unassigned, and external.

    External licenses are always in the external category, regardless of
    assignment status. This creates a clear three-table layout.

    Requires licenses.view permission.
    """
    validated_sort_by = validate_sort_by(sort_by, ALLOWED_LICENSE_SORT_COLUMNS, "external_user_id")
    return await license_service.get_categorized_licenses(
        provider_id=provider_id,
        sort_by=validated_sort_by,
        sort_dir=sort_dir,
    )


class PendingSuggestionsResponse(BaseModel):
    """Response for pending suggestions endpoint."""

    total: int
    items: list[LicenseResponse]


@router.get("/suggestions/pending", response_model=PendingSuggestionsResponse)
async def get_pending_suggestions(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    provider_id: UUID | None = None,
) -> PendingSuggestionsResponse:
    """Get all licenses with pending match suggestions.

    Returns licenses that have a suggested_employee_id but are not yet
    confirmed or rejected. Useful for review workflows.

    Requires licenses.view permission.
    """
    categorized = await license_service.get_categorized_licenses(
        provider_id=provider_id,
        sort_by="external_user_id",
        sort_dir="asc",
    )
    return PendingSuggestionsResponse(
        total=len(categorized.suggested),
        items=categorized.suggested,
    )


@router.get("/{license_id}", response_model=LicenseResponse)
async def get_license(
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
) -> LicenseResponse:
    """Get a single license by ID. Requires licenses.view permission."""
    license = await license_service.get_license(license_id)
    if license is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    return license


@router.post("/{license_id}/assign", response_model=LicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def assign_license(
    request: Request,
    license_id: UUID,
    body: AssignLicenseRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> LicenseResponse:
    """Manually assign a license to an employee. Requires licenses.assign permission."""
    license = await license_service.assign_license_to_employee(
        license_id,
        body.employee_id,
        user=current_user,
        request=request,
    )
    if license is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    return license


@router.post("/{license_id}/unassign", response_model=LicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def unassign_license(
    request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> LicenseResponse:
    """Unassign a license from an employee. Requires licenses.assign permission."""
    license = await license_service.unassign_license(
        license_id,
        user=current_user,
        request=request,
    )
    if license is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    return license


@router.post("/{license_id}/remove-from-provider", response_model=RemoveMemberResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def remove_license_from_provider(
    request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> RemoveMemberResponse:
    """Remove a user from the provider system. Requires licenses.delete permission.

    This will attempt to remove the user from the external provider (e.g., Cursor).
    Currently supported providers: Cursor (Enterprise only).
    """
    try:
        result = await license_service.remove_from_provider(
            license_id=license_id,
            user=current_user,
            request=request,
        )
        return RemoveMemberResponse(
            success=result["success"],
            message=result["message"],
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid license or operation not supported",
        )


@router.post("/bulk/remove-from-provider", response_model=BulkActionResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def bulk_remove_from_provider(
    request: Request,
    body: BulkActionRequest,
    current_user: Annotated[
        AdminUser, Depends(require_permission(Permissions.LICENSES_BULK_ACTIONS))
    ],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> BulkActionResponse:
    """Remove multiple users from their provider systems. Requires licenses.bulk_actions permission.

    This will attempt to remove each user from their external provider.
    Currently supported providers: Cursor (Enterprise only).
    Licenses from unsupported providers will be skipped with an error message.
    """
    if len(body.license_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 licenses per bulk operation",
        )

    result = await license_service.bulk_remove_from_provider(
        license_ids=body.license_ids,
        user=current_user,
        request=request,
    )

    return BulkActionResponse(
        total=result["total"],
        successful=result["successful"],
        failed=result["failed"],
        results=[
            BulkActionResult(
                license_id=r["license_id"],
                success=r["success"],
                message=r["message"],
            )
            for r in result["results"]
        ],
    )


@router.post("/bulk/delete", response_model=BulkActionResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def bulk_delete_licenses(
    request: Request,
    body: BulkActionRequest,
    current_user: Annotated[
        AdminUser, Depends(require_permission(Permissions.LICENSES_BULK_ACTIONS))
    ],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> BulkActionResponse:
    """Delete multiple licenses from the database. Requires licenses.bulk_actions permission.

    This only removes the licenses from the local database.
    It does NOT remove users from the external provider systems.
    Use bulk/remove-from-provider for that.
    """
    if len(body.license_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 licenses per bulk operation",
        )

    deleted_count = await license_service.bulk_delete(
        license_ids=body.license_ids,
        user=current_user,
        request=request,
    )

    results = [
        BulkActionResult(
            license_id=str(lid),
            success=True,
            message="License deleted from database",
        )
        for lid in body.license_ids
    ]

    return BulkActionResponse(
        total=len(body.license_ids),
        successful=deleted_count,
        failed=len(body.license_ids) - deleted_count,
        results=results,
    )


@router.post("/bulk/unassign", response_model=BulkActionResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def bulk_unassign_licenses(
    request: Request,
    body: BulkActionRequest,
    current_user: Annotated[
        AdminUser, Depends(require_permission(Permissions.LICENSES_BULK_ACTIONS))
    ],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> BulkActionResponse:
    """Unassign multiple licenses from employees. Requires licenses.bulk_actions permission.

    This removes the employee association from the licenses,
    marking them as unassigned. The licenses remain in the database
    and the users remain in the external provider systems.
    """
    if len(body.license_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 licenses per bulk operation",
        )

    unassigned_count = await license_service.bulk_unassign(
        license_ids=body.license_ids,
        user=current_user,
        request=request,
    )

    results = [
        BulkActionResult(
            license_id=str(lid),
            success=True,
            message="License unassigned from employee",
        )
        for lid in body.license_ids
    ]

    return BulkActionResponse(
        total=len(body.license_ids),
        successful=unassigned_count,
        failed=len(body.license_ids) - unassigned_count,
        results=results,
    )


@router.put("/{license_id}/service-account", response_model=LicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_service_account_status(
    request: Request,
    license_id: UUID,
    data: ServiceAccountUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> LicenseResponse:
    """Mark or unmark a license as a service account. Requires licenses.edit permission.

    Service accounts are licenses that are intentionally not linked to HRIS employees.
    They appear in a separate category and don't count as "unassigned" problems.

    If apply_globally is True, the email address will be added to the global
    service account patterns list for automatic detection during sync.
    """
    result = await license_service.update_service_account_with_commit(
        license_id=license_id,
        is_service_account=data.is_service_account,
        service_account_name=data.service_account_name,
        service_account_owner_id=data.service_account_owner_id,
        apply_globally=data.apply_globally,
        user=current_user,
        request=request,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    license_response, _ = result
    return license_response


@router.put("/{license_id}/admin-account", response_model=LicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_admin_account_status(
    request: Request,
    license_id: UUID,
    data: AdminAccountUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> LicenseResponse:
    """Mark or unmark a license as an admin account. Requires licenses.edit permission.

    Admin accounts are personal elevated-privilege accounts (e.g., max-admin@firma.de)
    that belong to a specific employee. Unlike service accounts, admin accounts
    ARE linked to people and should be removed when the owner is offboarded.

    If the owner is offboarded, a warning will be shown in the dashboard.

    If apply_globally is True, the email address will be added to the global
    admin account patterns list for automatic detection during sync.
    """
    result = await license_service.update_admin_account_with_commit(
        license_id=license_id,
        is_admin_account=data.is_admin_account,
        admin_account_name=data.admin_account_name,
        admin_account_owner_id=data.admin_account_owner_id,
        apply_globally=data.apply_globally,
        user=current_user,
        request=request,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    license_response, _ = result
    return license_response


@router.put("/{license_id}/license-type", response_model=LicenseResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_license_type(
    request: Request,
    license_id: UUID,
    data: LicenseTypeUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> LicenseResponse:
    """Update the license type for a license. Requires licenses.edit permission.

    This is useful for providers like Figma where the license type cannot be
    automatically detected (Business plan without Enterprise roles).
    """
    result = await license_service.update_license_type_with_commit(
        license_id=license_id,
        license_type=data.license_type,
        user=current_user,
        request=request,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    return result


# Match management endpoints


@router.post("/{license_id}/match/confirm", response_model=MatchActionResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def confirm_match(
    request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> MatchActionResponse:
    """Confirm a suggested match for a license. Requires licenses.assign permission.

    This will move the suggested employee to the confirmed employee assignment.
    GDPR: No private email addresses are stored.
    """
    license_orm = await matching_service.confirm_match_with_commit(
        license_id=license_id,
        user=current_user,
        request=request,
    )

    if license_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found or no suggested match to confirm",
        )

    license_response = await license_service.get_license(license_id)

    return MatchActionResponse(
        success=True,
        message="Match confirmed successfully",
        license=license_response,
    )


@router.post("/{license_id}/match/reject", response_model=MatchActionResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def reject_match(
    request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> MatchActionResponse:
    """Reject a suggested match for a license. Requires licenses.assign permission.

    This will clear the suggested match and mark the license as rejected.
    """
    license_orm = await matching_service.reject_match_with_commit(
        license_id=license_id,
        user=current_user,
        request=request,
    )

    if license_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    license_response = await license_service.get_license(license_id)

    return MatchActionResponse(
        success=True,
        message="Match rejected",
        license=license_response,
    )


@router.post("/{license_id}/match/external-guest", response_model=MatchActionResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def mark_as_external_guest(
    request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> MatchActionResponse:
    """Mark a license as belonging to an external guest. Requires licenses.edit permission.

    This confirms that the license is intentionally assigned to someone outside the company.
    """
    license_orm = await matching_service.mark_as_external_guest_with_commit(
        license_id=license_id,
        user=current_user,
        request=request,
    )

    if license_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    license_response = await license_service.get_license(license_id)

    return MatchActionResponse(
        success=True,
        message="Marked as external guest",
        license=license_response,
    )


@router.post("/{license_id}/match/assign", response_model=MatchActionResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def manual_assign_match(
    request: Request,
    license_id: UUID,
    body: ManualAssignRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> MatchActionResponse:
    """Manually assign a license to an employee.

    Requires licenses.assign permission.
    GDPR: No private email addresses are stored.
    """
    license_orm = await matching_service.assign_to_employee_with_commit(
        license_id=license_id,
        employee_id=body.employee_id,
        user=current_user,
        request=request,
    )

    if license_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    license_response = await license_service.get_license(license_id)

    return MatchActionResponse(
        success=True,
        message="License assigned successfully",
        license=license_response,
    )
