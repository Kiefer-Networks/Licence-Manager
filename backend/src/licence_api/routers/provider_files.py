"""Provider files router for document uploads."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from licence_api.dependencies import get_provider_file_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import (
    API_DEFAULT_LIMIT,
    EXPENSIVE_READ_LIMIT,
    SENSITIVE_OPERATION_LIMIT,
    limiter,
)
from licence_api.services.provider_file_service import (
    VIEWABLE_EXTENSIONS,
    ProviderFileService,
)
from licence_api.utils.errors import raise_bad_request, raise_not_found

# Maximum provider file upload size: 50MB
MAX_PROVIDER_FILE_SIZE = 50 * 1024 * 1024

router = APIRouter()


class ProviderFileResponse(BaseModel):
    """Provider file response."""

    id: UUID
    provider_id: UUID
    filename: str
    original_name: str
    file_type: str
    file_size: int
    description: str | None
    category: str | None
    created_at: str
    viewable: bool

    class Config:
        from_attributes = True


class ProviderFilesListResponse(BaseModel):
    """Provider files list response."""

    items: list[ProviderFileResponse]
    total: int


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
        files = await service.list_files(provider_id)
    except ValueError:
        raise_not_found("Provider")

    items = [
        ProviderFileResponse(
            id=f.id,
            provider_id=f.provider_id,
            filename=f.filename,
            original_name=f.original_name,
            file_type=f.file_type,
            file_size=f.file_size,
            description=f.description,
            category=f.category,
            created_at=f.created_at.isoformat(),
            viewable=Path(f.filename).suffix.lower() in VIEWABLE_EXTENSIONS,
        )
        for f in files
    ]

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
        file_orm = await service.upload_file(
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

    ext = Path(file_orm.filename).suffix.lower()
    return ProviderFileResponse(
        id=file_orm.id,
        provider_id=file_orm.provider_id,
        filename=file_orm.filename,
        original_name=file_orm.original_name,
        file_type=file_orm.file_type,
        file_size=file_orm.file_size,
        description=file_orm.description,
        category=file_orm.category,
        created_at=file_orm.created_at.isoformat(),
        viewable=ext in VIEWABLE_EXTENSIONS,
    )


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

    ext = Path(file_orm.filename).suffix.lower()
    if ext not in VIEWABLE_EXTENSIONS:
        raise_bad_request("This file type cannot be viewed inline. Use download instead.")

    file_path = service.get_file_path(provider_id, file_orm.filename)
    if file_path is None:
        raise_not_found("File on disk")

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
