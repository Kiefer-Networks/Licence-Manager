"""Provider files router for document uploads."""

import os
import uuid
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.orm.provider_file import ProviderFileORM
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.security.auth import get_current_user, require_admin

router = APIRouter()

# File storage directory
FILES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "files"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Allowed file extensions - only office documents, images, and PDFs
ALLOWED_EXTENSIONS = {
    # PDFs
    ".pdf",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
    # Microsoft Office
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # OpenDocument
    ".odt", ".ods", ".odp",
}

# File types that can be viewed inline in browser
VIEWABLE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

# MIME types for viewable files
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
}

# Magic bytes for file type validation - ALL allowed types must have signatures
FILE_SIGNATURES = {
    # PDF
    ".pdf": [b"%PDF"],
    # Images
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".gif": [b"GIF87a", b"GIF89a"],
    ".webp": [b"RIFF"],  # RIFF container, followed by WEBP
    ".bmp": [b"BM"],
    # Microsoft Office - OLE compound documents (legacy .doc, .xls, .ppt)
    ".doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".xls": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".ppt": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    # Office Open XML (ZIP archives) - .docx, .xlsx, .pptx
    ".docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    ".xlsx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    ".pptx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    # OpenDocument (also ZIP archives)
    ".odt": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    ".ods": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    ".odp": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
}


def validate_file_signature(content: bytes, extension: str) -> bool:
    """Validate file content matches expected signature for extension.

    Args:
        content: File content bytes
        extension: File extension (e.g., ".pdf")

    Returns:
        True if file signature matches expected type

    Raises:
        ValueError if extension has no signature defined (should not happen for allowed types)
    """
    ext_lower = extension.lower()
    signatures = FILE_SIGNATURES.get(ext_lower)

    if not signatures:
        # All allowed extensions must have signatures defined
        raise ValueError(f"No signature defined for extension: {ext_lower}")

    # Special handling for WEBP which is RIFF container
    if ext_lower == ".webp":
        # Must start with RIFF and contain WEBP
        if content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WEBP":
            return True
        return False

    for sig in signatures:
        if content.startswith(sig):
            return True
    return False


def get_safe_mime_type(extension: str, fallback: str = "application/octet-stream") -> str:
    """Get MIME type for extension, with safe fallback."""
    return MIME_TYPES.get(extension.lower(), fallback)


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
    viewable: bool  # Whether file can be viewed inline in browser

    class Config:
        from_attributes = True


class ProviderFilesListResponse(BaseModel):
    """Provider files list response."""
    items: list[ProviderFileResponse]
    total: int


@router.get("/{provider_id}/files", response_model=ProviderFilesListResponse)
async def list_provider_files(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderFilesListResponse:
    """List all files for a provider."""
    # Check provider exists
    repo = ProviderRepository(db)
    provider = await repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    result = await db.execute(
        select(ProviderFileORM)
        .where(ProviderFileORM.provider_id == provider_id)
        .order_by(ProviderFileORM.created_at.desc())
    )
    files = list(result.scalars().all())

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


@router.post("/{provider_id}/files", response_model=ProviderFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_provider_file(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    category: str | None = Form(default=None),
) -> ProviderFileResponse:
    """Upload a file for a provider. Admin only."""
    # Check provider exists
    repo = ProviderRepository(db)
    provider = await repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Validate file
    if file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    # Sanitize filename - only keep basename
    safe_filename = Path(file.filename).name
    if not safe_filename or "/" in safe_filename or "\\" in safe_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file signature (magic bytes)
    if not validate_file_signature(content, ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match declared file type",
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB",
        )

    # Generate unique filename
    stored_filename = f"{uuid.uuid4()}{ext}"
    provider_dir = FILES_DIR / str(provider_id)
    provider_dir.mkdir(parents=True, exist_ok=True)
    file_path = provider_dir / stored_filename

    # Save file
    file_path.write_bytes(content)

    # Create database record - use our validated MIME type, not the client-provided one
    file_orm = ProviderFileORM(
        provider_id=provider_id,
        filename=stored_filename,
        original_name=file.filename,
        file_type=get_safe_mime_type(ext),
        file_size=file_size,
        description=description,
        category=category,
    )
    db.add(file_orm)
    await db.commit()
    await db.refresh(file_orm)

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
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """Download a provider file."""
    result = await db.execute(
        select(ProviderFileORM)
        .where(ProviderFileORM.id == file_id)
        .where(ProviderFileORM.provider_id == provider_id)
    )
    file_orm = result.scalar_one_or_none()

    if file_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file_path = FILES_DIR / str(provider_id) / file_orm.filename

    # Validate path is within FILES_DIR (prevent path traversal)
    try:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(FILES_DIR.resolve()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
    except (ValueError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk",
        )

    return FileResponse(
        path=file_path,
        filename=file_orm.original_name,
        media_type=file_orm.file_type,
    )


@router.get("/{provider_id}/files/{file_id}/view")
async def view_provider_file(
    provider_id: UUID,
    file_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """View a provider file inline in browser (PDFs and images only)."""
    result = await db.execute(
        select(ProviderFileORM)
        .where(ProviderFileORM.id == file_id)
        .where(ProviderFileORM.provider_id == provider_id)
    )
    file_orm = result.scalar_one_or_none()

    if file_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Check if file is viewable
    ext = Path(file_orm.filename).suffix.lower()
    if ext not in VIEWABLE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This file type cannot be viewed inline. Use download instead.",
        )

    file_path = FILES_DIR / str(provider_id) / file_orm.filename

    # Validate path is within FILES_DIR (prevent path traversal)
    try:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(FILES_DIR.resolve()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
    except (ValueError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk",
        )

    # Return file for inline viewing (no Content-Disposition: attachment)
    return FileResponse(
        path=file_path,
        media_type=get_safe_mime_type(ext),
        # Don't set filename to allow inline viewing
    )


@router.delete("/{provider_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_file(
    provider_id: UUID,
    file_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a provider file. Admin only."""
    result = await db.execute(
        select(ProviderFileORM)
        .where(ProviderFileORM.id == file_id)
        .where(ProviderFileORM.provider_id == provider_id)
    )
    file_orm = result.scalar_one_or_none()

    if file_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Delete file from disk
    file_path = FILES_DIR / str(provider_id) / file_orm.filename
    if file_path.exists():
        file_path.unlink()

    # Delete from database
    await db.delete(file_orm)
    await db.commit()
