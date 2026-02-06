"""Provider files router for document uploads."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.repositories.provider_file_repository import ProviderFileRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.csrf import CSRFProtected
from licence_api.security.rate_limit import SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.provider_file_service import (
    VIEWABLE_EXTENSIONS,
    ProviderFileService,
)
from licence_api.utils.errors import raise_bad_request, raise_not_found

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


# Dependency injection functions
def get_provider_repository(db: AsyncSession = Depends(get_db)) -> ProviderRepository:
    """Get ProviderRepository instance."""
    return ProviderRepository(db)


def get_provider_file_repository(db: AsyncSession = Depends(get_db)) -> ProviderFileRepository:
    """Get ProviderFileRepository instance."""
    return ProviderFileRepository(db)


def get_provider_file_service(db: AsyncSession = Depends(get_db)) -> ProviderFileService:
    """Get ProviderFileService instance."""
    return ProviderFileService(db)


@router.get("/{provider_id}/files", response_model=ProviderFilesListResponse)
async def list_provider_files(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    file_repo: Annotated[ProviderFileRepository, Depends(get_provider_file_repository)],
) -> ProviderFilesListResponse:
    """List all files for a provider."""
    provider = await provider_repo.get_by_id(provider_id)
    if provider is None:
        raise_not_found("Provider")

    files = await file_repo.get_by_provider(provider_id)

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
    _csrf: Annotated[None, Depends(CSRFProtected())],
    file: UploadFile = File(...),
    description: str | None = Form(default=None, max_length=2000),
    category: str | None = Form(default=None, max_length=100),
) -> ProviderFileResponse:
    """Upload a file for a provider. Admin only.

    Note: CSRF protection is explicitly applied via CSRFProtected dependency.
    """
    if file.filename is None:
        raise_bad_request("No filename provided")

    content = await file.read()

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
async def download_provider_file(
    provider_id: UUID,
    file_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    file_repo: Annotated[ProviderFileRepository, Depends(get_provider_file_repository)],
    service: Annotated[ProviderFileService, Depends(get_provider_file_service)],
) -> FileResponse:
    """Download a provider file."""
    file_orm = await file_repo.get_by_provider_and_id(provider_id, file_id)

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
async def view_provider_file(
    provider_id: UUID,
    file_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    file_repo: Annotated[ProviderFileRepository, Depends(get_provider_file_repository)],
    service: Annotated[ProviderFileService, Depends(get_provider_file_service)],
) -> FileResponse:
    """View a provider file inline in browser (PDFs and images only)."""
    file_orm = await file_repo.get_by_provider_and_id(provider_id, file_id)

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
    _csrf: Annotated[None, Depends(CSRFProtected())],
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
