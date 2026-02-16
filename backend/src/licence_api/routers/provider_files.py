"""Provider files router for document uploads."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from licence_api.dependencies import get_provider_file_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.provider_file import ProviderFileResponse, ProviderFilesListResponse
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import (
    API_DEFAULT_LIMIT,
    EXPENSIVE_READ_LIMIT,
    SENSITIVE_OPERATION_LIMIT,
    limiter,
)
from licence_api.services.provider_file_service import ProviderFileService
from licence_api.utils.errors import raise_bad_request, raise_not_found

# Maximum provider file upload size: 50MB
MAX_PROVIDER_FILE_SIZE = 50 * 1024 * 1024

router = APIRouter()


@router.get("/{provider_id}/files", response_model=ProviderFilesListResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_provider_files(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    service: Annotated[ProviderFileService, Depends(get_provider_file_service)],
) -> ProviderFilesListResponse:
    """List all files for a provider."""
    try:
        items = await service.list_files(provider_id)
    except ValueError:
        raise_not_found("Provider")

    return ProviderFilesListResponse(items=items, total=len(items))


@router.post(
    "/{provider_id}/files", response_model=ProviderFileResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def upload_provider_file(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    service: Annotated[ProviderFileService, Depends(get_provider_file_service)],
    file: UploadFile = File(...),
    description: str | None = Form(default=None, max_length=2000),
    category: str | None = Form(default=None, max_length=100),
) -> ProviderFileResponse:
    """Upload a file for a provider. Admin only.

    Note: CSRF protection is handled by CSRFMiddleware.
    """
    if file.filename is None:
        raise_bad_request("No filename provided")

    content = await file.read(MAX_PROVIDER_FILE_SIZE + 1)
    if len(content) > MAX_PROVIDER_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_PROVIDER_FILE_SIZE // 1024 // 1024}MB",
        )

    try:
        return await service.upload_file(
            provider_id=provider_id,
            filename=file.filename,
            content=content,
            description=description,
            category=category,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_bad_request("Invalid file or provider not found")


@router.get("/{provider_id}/files/{file_id}/download")
@limiter.limit(API_DEFAULT_LIMIT)
async def download_provider_file(
    request: Request,
    provider_id: UUID,
    file_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    service: Annotated[ProviderFileService, Depends(get_provider_file_service)],
) -> FileResponse:
    """Download a provider file."""
    file_orm = await service.get_file(provider_id, file_id)

    if file_orm is None:
        raise_not_found("File")

    file_path = service.get_file_path(provider_id, file_orm.filename)
    if file_path is None:
        raise_not_found("File on disk")

    return FileResponse(
        path=file_path,
        filename=file_orm.original_name,
        media_type=file_orm.file_type,
    )


@router.get("/{provider_id}/files/{file_id}/view")
@limiter.limit(API_DEFAULT_LIMIT)
async def view_provider_file(
    request: Request,
    provider_id: UUID,
    file_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    service: Annotated[ProviderFileService, Depends(get_provider_file_service)],
) -> FileResponse:
    """View a provider file inline in browser (PDFs and images only)."""
    file_orm = await service.get_file(provider_id, file_id)

    if file_orm is None:
        raise_not_found("File")

    if not ProviderFileService.is_viewable(file_orm.filename):
        raise_bad_request("This file type cannot be viewed inline. Use download instead.")

    file_path = service.get_file_path(provider_id, file_orm.filename)
    if file_path is None:
        raise_not_found("File on disk")

    ext = Path(file_orm.filename).suffix.lower()
    return FileResponse(
        path=file_path,
        media_type=ProviderFileService.get_safe_mime_type(ext),
    )


@router.delete("/{provider_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_provider_file(
    request: Request,
    provider_id: UUID,
    file_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_DELETE))],
    service: Annotated[ProviderFileService, Depends(get_provider_file_service)],
) -> None:
    """Delete a provider file. Requires providers.delete permission."""
    try:
        await service.delete_file(
            provider_id=provider_id,
            file_id=file_id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise_not_found("File")
