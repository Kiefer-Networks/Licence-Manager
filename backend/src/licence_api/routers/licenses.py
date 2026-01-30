"""Licenses router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.domain.provider import ProviderName
from licence_api.models.dto.license import (
    LicenseResponse,
    LicenseListResponse,
    CategorizedLicensesResponse,
)
from licence_api.security.auth import get_current_user, require_admin, require_permission, Permissions
from licence_api.security.encryption import get_encryption_service
from licence_api.services.license_service import LicenseService
from licence_api.utils.validation import sanitize_department, sanitize_search, sanitize_status
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.license_repository import LicenseRepository

router = APIRouter()


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


# Allowed status values for licenses
ALLOWED_LICENSE_STATUSES = {"active", "inactive", "suspended", "pending"}


@router.get("", response_model=LicenseListResponse)
async def list_licenses(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
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

    service = LicenseService(db)
    return await service.list_licenses(
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
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_id: UUID | None = None,
    sort_by: str = Query(default="external_user_id", max_length=50),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> CategorizedLicensesResponse:
    """Get licenses categorized into assigned, unassigned, and external.

    External licenses are always in the external category, regardless of
    assignment status. This creates a clear three-table layout.

    Requires licenses.view permission.
    """
    service = LicenseService(db)
    return await service.get_categorized_licenses(
        provider_id=provider_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/{license_id}", response_model=LicenseResponse)
async def get_license(
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseResponse:
    """Get a single license by ID. Requires licenses.view permission."""
    service = LicenseService(db)
    license = await service.get_license(license_id)
    if license is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    return license


@router.post("/{license_id}/assign", response_model=LicenseResponse)
async def assign_license(
    license_id: UUID,
    request: AssignLicenseRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseResponse:
    """Manually assign a license to an employee. Requires licenses.assign permission."""
    service = LicenseService(db)
    license = await service.assign_license_to_employee(license_id, request.employee_id)
    if license is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    return license


@router.post("/{license_id}/unassign", response_model=LicenseResponse)
async def unassign_license(
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_ASSIGN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseResponse:
    """Unassign a license from an employee. Requires licenses.assign permission."""
    service = LicenseService(db)
    license = await service.unassign_license(license_id)
    if license is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    return license


@router.post("/{license_id}/remove-from-provider", response_model=RemoveMemberResponse)
async def remove_license_from_provider(
    license_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_DELETE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RemoveMemberResponse:
    """Remove a user from the provider system. Requires licenses.delete permission.

    This will attempt to remove the user from the external provider (e.g., Cursor).
    Currently supported providers: Cursor (Enterprise only).
    """
    from licence_api.providers import CursorProvider

    license_repo = LicenseRepository(db)
    provider_repo = ProviderRepository(db)

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
    request: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_BULK_ACTIONS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkActionResponse:
    """Remove multiple users from their provider systems. Requires licenses.bulk_actions permission.

    This will attempt to remove each user from their external provider.
    Currently supported providers: Cursor (Enterprise only).
    Licenses from unsupported providers will be skipped with an error message.
    """
    from licence_api.providers import CursorProvider

    license_repo = LicenseRepository(db)
    provider_repo = ProviderRepository(db)
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

    await db.commit()

    return BulkActionResponse(
        total=len(request.license_ids),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.post("/bulk/delete", response_model=BulkActionResponse)
async def bulk_delete_licenses(
    request: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_BULK_ACTIONS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkActionResponse:
    """Delete multiple licenses from the database. Requires licenses.bulk_actions permission.

    This only removes the licenses from the local database.
    It does NOT remove users from the external provider systems.
    Use bulk/remove-from-provider for that.
    """
    license_repo = LicenseRepository(db)

    if len(request.license_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 licenses per bulk operation",
        )

    deleted_count = await license_repo.delete_by_ids(request.license_ids)
    await db.commit()

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
    request: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_BULK_ACTIONS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkActionResponse:
    """Unassign multiple licenses from employees. Requires licenses.bulk_actions permission.

    This removes the employee association from the licenses,
    marking them as unassigned. The licenses remain in the database
    and the users remain in the external provider systems.
    """
    license_repo = LicenseRepository(db)

    if len(request.license_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 licenses per bulk operation",
        )

    unassigned_count = await license_repo.unassign_by_ids(request.license_ids)
    await db.commit()

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
