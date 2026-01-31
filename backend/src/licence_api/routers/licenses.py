"""Licenses router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.domain.provider import ProviderName
from licence_api.models.dto.license import (
    LicenseResponse,
    LicenseListResponse,
    CategorizedLicensesResponse,
    ServiceAccountUpdate,
    AdminAccountUpdate,
)
from licence_api.security.auth import get_current_user, require_permission, Permissions
from licence_api.security.encryption import get_encryption_service
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
from licence_api.services.license_service import LicenseService
from licence_api.services.matching_service import MatchingService
from licence_api.utils.validation import sanitize_department, sanitize_search, sanitize_status
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.license_repository import LicenseRepository

router = APIRouter()


# Dependency injection functions
def get_license_service(db: AsyncSession = Depends(get_db)) -> LicenseService:
    """Get LicenseService instance."""
    return LicenseService(db)


def get_license_repository(db: AsyncSession = Depends(get_db)) -> LicenseRepository:
    """Get LicenseRepository instance."""
    return LicenseRepository(db)


def get_provider_repository(db: AsyncSession = Depends(get_db)) -> ProviderRepository:
    """Get ProviderRepository instance."""
    return ProviderRepository(db)


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    """Get AuditService instance."""
    return AuditService(db)


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

    license_ids: list[UUID]


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
    department: str | None = Query(default=None, max_length=100, description="Filter by employee department"),
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

    return await license_service.list_licenses(
        provider_id=provider_id,
        employee_id=employee_id,
        status=sanitized_status,
        unassigned_only=unassigned,
        external_only=external,
        search=sanitized_search,
        department=sanitized_department,
        sort_by=sort_by,
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
    return await license_service.get_categorized_licenses(
        provider_id=provider_id,
        sort_by=sort_by,
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
async def assign_license(
    http_request: Request,
    license_id: UUID,
    request: AssignLicenseRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
) -> LicenseResponse:
    """Manually assign a license to an employee. Requires licenses.assign permission."""
    license = await license_service.assign_license_to_employee(
        license_id,
        request.employee_id,
        user=current_user,
        request=http_request,
    )
    if license is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    return license


@router.post("/{license_id}/unassign", response_model=LicenseResponse)
async def unassign_license(
    http_request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
) -> LicenseResponse:
    """Unassign a license from an employee. Requires licenses.assign permission."""
    license = await license_service.unassign_license(
        license_id,
        user=current_user,
        request=http_request,
    )
    if license is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    return license


@router.post("/{license_id}/remove-from-provider", response_model=RemoveMemberResponse)
async def remove_license_from_provider(
    http_request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    db: Annotated[AsyncSession, Depends(get_db)],
    license_repo: Annotated[LicenseRepository, Depends(get_license_repository)],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> RemoveMemberResponse:
    """Remove a user from the provider system. Requires licenses.delete permission.

    This will attempt to remove the user from the external provider (e.g., Cursor).
    Currently supported providers: Cursor (Enterprise only).
    """
    from licence_api.providers import CursorProvider

    # Get the license
    license_orm = await license_repo.get_by_id(license_id)
    if license_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    # Get the provider
    provider = await provider_repo.get_by_id(license_orm.provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Check if provider supports remote removal
    if provider.name != ProviderName.CURSOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider {provider.display_name} does not support remote user removal",
        )

    # Decrypt credentials and create provider instance
    encryption = get_encryption_service()
    credentials = encryption.decrypt(provider.credentials_encrypted)

    try:
        cursor_provider = CursorProvider(credentials)
        result = await cursor_provider.remove_member(license_orm.external_user_id)

        # If successful, delete the license from our database
        if result["success"]:
            await license_repo.delete(license_id)

            # Audit log the deletion
            await audit_service.log(
                action=AuditAction.LICENSE_DELETE,
                resource_type=ResourceType.LICENSE,
                resource_id=license_id,
                admin_user_id=current_user.id,
                changes={
                    "external_user_id": license_orm.external_user_id,
                    "provider": provider.display_name,
                    "removed_from_provider": True,
                },
                request=http_request,
            )
            await db.commit()

        return RemoveMemberResponse(
            success=result["success"],
            message=result["message"],
        )
    except ValueError as e:
        return RemoveMemberResponse(
            success=False,
            message=str(e),
        )


@router.post("/bulk/remove-from-provider", response_model=BulkActionResponse)
async def bulk_remove_from_provider(
    http_request: Request,
    request: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_BULK_ACTIONS))],
    db: Annotated[AsyncSession, Depends(get_db)],
    license_repo: Annotated[LicenseRepository, Depends(get_license_repository)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> BulkActionResponse:
    """Remove multiple users from their provider systems. Requires licenses.bulk_actions permission.

    This will attempt to remove each user from their external provider.
    Currently supported providers: Cursor (Enterprise only).
    Licenses from unsupported providers will be skipped with an error message.
    """
    from licence_api.providers import CursorProvider

    encryption = get_encryption_service()

    if len(request.license_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 licenses per bulk operation",
        )

    # Fetch all licenses with their providers
    licenses_with_providers = await license_repo.get_by_ids_with_providers(request.license_ids)

    # Group by provider for efficient credential decryption
    provider_credentials: dict[UUID, dict] = {}
    results: list[BulkActionResult] = []
    successful = 0
    failed = 0
    deleted_license_ids: list[UUID] = []

    for license_orm, provider in licenses_with_providers:
        # Check if provider supports remote removal
        if provider.name != ProviderName.CURSOR:
            results.append(BulkActionResult(
                license_id=str(license_orm.id),
                success=False,
                message=f"Provider {provider.display_name} does not support remote user removal",
            ))
            failed += 1
            continue

        # Get or decrypt credentials
        if provider.id not in provider_credentials:
            provider_credentials[provider.id] = encryption.decrypt(provider.credentials_encrypted)

        try:
            cursor_provider = CursorProvider(provider_credentials[provider.id])
            result = await cursor_provider.remove_member(license_orm.external_user_id)

            if result["success"]:
                await license_repo.delete(license_orm.id)
                deleted_license_ids.append(license_orm.id)
                successful += 1
                results.append(BulkActionResult(
                    license_id=str(license_orm.id),
                    success=True,
                    message=result["message"],
                ))
            else:
                failed += 1
                results.append(BulkActionResult(
                    license_id=str(license_orm.id),
                    success=False,
                    message=result.get("message", "Unknown error"),
                ))
        except ValueError as e:
            failed += 1
            results.append(BulkActionResult(
                license_id=str(license_orm.id),
                success=False,
                message=str(e),
            ))

    # Audit log the bulk operation
    if deleted_license_ids:
        await audit_service.log(
            action=AuditAction.LICENSE_DELETE,
            resource_type=ResourceType.LICENSE,
            admin_user_id=current_user.id,
            changes={
                "bulk_operation": True,
                "deleted_count": len(deleted_license_ids),
                "deleted_ids": [str(lid) for lid in deleted_license_ids],
                "removed_from_provider": True,
            },
            request=http_request,
        )

    await db.commit()

    return BulkActionResponse(
        total=len(request.license_ids),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.post("/bulk/delete", response_model=BulkActionResponse)
async def bulk_delete_licenses(
    http_request: Request,
    request: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_BULK_ACTIONS))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
) -> BulkActionResponse:
    """Delete multiple licenses from the database. Requires licenses.bulk_actions permission.

    This only removes the licenses from the local database.
    It does NOT remove users from the external provider systems.
    Use bulk/remove-from-provider for that.
    """
    if len(request.license_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 licenses per bulk operation",
        )

    deleted_count = await license_service.bulk_delete(
        license_ids=request.license_ids,
        user=current_user,
        request=http_request,
    )

    results = [
        BulkActionResult(
            license_id=str(lid),
            success=True,
            message="License deleted from database",
        )
        for lid in request.license_ids
    ]

    return BulkActionResponse(
        total=len(request.license_ids),
        successful=deleted_count,
        failed=len(request.license_ids) - deleted_count,
        results=results,
    )


@router.post("/bulk/unassign", response_model=BulkActionResponse)
async def bulk_unassign_licenses(
    http_request: Request,
    request: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_BULK_ACTIONS))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
) -> BulkActionResponse:
    """Unassign multiple licenses from employees. Requires licenses.bulk_actions permission.

    This removes the employee association from the licenses,
    marking them as unassigned. The licenses remain in the database
    and the users remain in the external provider systems.
    """
    if len(request.license_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 licenses per bulk operation",
        )

    unassigned_count = await license_service.bulk_unassign(
        license_ids=request.license_ids,
        user=current_user,
        request=http_request,
    )

    results = [
        BulkActionResult(
            license_id=str(lid),
            success=True,
            message="License unassigned from employee",
        )
        for lid in request.license_ids
    ]

    return BulkActionResponse(
        total=len(request.license_ids),
        successful=unassigned_count,
        failed=len(request.license_ids) - unassigned_count,
        results=results,
    )


@router.put("/{license_id}/service-account", response_model=LicenseResponse)
async def update_service_account_status(
    http_request: Request,
    license_id: UUID,
    data: ServiceAccountUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
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
        request=http_request,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    license_response, _ = result
    return license_response


@router.put("/{license_id}/admin-account", response_model=LicenseResponse)
async def update_admin_account_status(
    http_request: Request,
    license_id: UUID,
    data: AdminAccountUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
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
        request=http_request,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )

    license_response, _ = result
    return license_response


# Match management endpoints

@router.post("/{license_id}/match/confirm", response_model=MatchActionResponse)
async def confirm_match(
    http_request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
) -> MatchActionResponse:
    """Confirm a suggested match for a license. Requires licenses.assign permission.

    This will move the suggested employee to the confirmed employee assignment.
    GDPR: No private email addresses are stored.
    """
    license_orm = await matching_service.confirm_match_with_commit(
        license_id=license_id,
        user=current_user,
        request=http_request,
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
async def reject_match(
    http_request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
) -> MatchActionResponse:
    """Reject a suggested match for a license. Requires licenses.assign permission.

    This will clear the suggested match and mark the license as rejected.
    """
    license_orm = await matching_service.reject_match_with_commit(
        license_id=license_id,
        user=current_user,
        request=http_request,
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
async def mark_as_external_guest(
    http_request: Request,
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_EDIT))],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
) -> MatchActionResponse:
    """Mark a license as belonging to an external guest. Requires licenses.edit permission.

    This confirms that the license is intentionally assigned to someone outside the company.
    """
    license_orm = await matching_service.mark_as_external_guest_with_commit(
        license_id=license_id,
        user=current_user,
        request=http_request,
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
async def manual_assign_match(
    http_request: Request,
    license_id: UUID,
    request: ManualAssignRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
    license_service: Annotated[LicenseService, Depends(get_license_service)],
) -> MatchActionResponse:
    """Manually assign a license to an employee.

    Requires licenses.assign permission.
    GDPR: No private email addresses are stored.
    """
    license_orm = await matching_service.assign_to_employee_with_commit(
        license_id=license_id,
        employee_id=request.employee_id,
        user=current_user,
        request=http_request,
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
