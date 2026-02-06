"""Provider file service for managing provider documents."""

import logging
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.constants.paths import FILES_DIR
from licence_api.models.domain.admin_user import AdminUser
from licence_api.repositories.provider_file_repository import ProviderFileRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
from licence_api.utils.secure_logging import log_warning

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Allowed file extensions - only office documents, images, and PDFs
ALLOWED_EXTENSIONS = {
    # PDFs
    ".pdf",
    # Images
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    # Microsoft Office
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    # OpenDocument
    ".odt",
    ".ods",
    ".odp",
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

# Magic bytes for file type validation
FILE_SIGNATURES = {
    ".pdf": [b"%PDF"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".gif": [b"GIF87a", b"GIF89a"],
    ".webp": [b"RIFF"],
    ".bmp": [b"BM"],
    ".doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".xls": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".ppt": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    ".xlsx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    ".pptx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    ".odt": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    ".ods": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    ".odp": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
}


class ProviderFileService:
    """Service for managing provider files."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.file_repo = ProviderFileRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.audit_service = AuditService(session)

    @staticmethod
    def validate_file_signature(content: bytes, extension: str) -> bool:
        """Validate file content matches expected signature for extension."""
        ext_lower = extension.lower()
        signatures = FILE_SIGNATURES.get(ext_lower)

        if not signatures:
            raise ValueError(f"No signature defined for extension: {ext_lower}")

        if ext_lower == ".webp":
            if content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WEBP":
                return True
            return False

        for sig in signatures:
            if content.startswith(sig):
                return True
        return False

    @staticmethod
    def get_safe_mime_type(extension: str, fallback: str = "application/octet-stream") -> str:
        """Get MIME type for extension, with safe fallback."""
        return MIME_TYPES.get(extension.lower(), fallback)

    @staticmethod
    def validate_file_path(file_path: Path, base_dir: Path) -> bool:
        """Validate that file path is within base directory."""
        try:
            resolved = file_path.resolve()
            return resolved.is_relative_to(base_dir.resolve())
        except (ValueError, RuntimeError):
            return False

    async def upload_file(
        self,
        provider_id: UUID,
        filename: str,
        content: bytes,
        description: str | None = None,
        category: str | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> "ProviderFileORM":
        """Upload a file for a provider.

        Args:
            provider_id: Provider UUID
            filename: Original filename
            content: File content bytes
            description: Optional description
            category: Optional category
            user: Admin user uploading the file
            request: HTTP request for audit logging

        Returns:
            Created ProviderFileORM

        Raises:
            ValueError: If validation fails
        """

        # Check provider exists
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        # Sanitize filename
        safe_filename = Path(filename).name
        if not safe_filename or "/" in safe_filename or "\\" in safe_filename:
            raise ValueError("Invalid filename")

        ext = Path(safe_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB")

        # Validate file signature
        if not self.validate_file_signature(content, ext):
            raise ValueError("File content does not match declared file type")

        # Generate unique filename and save to disk
        stored_filename = f"{uuid.uuid4()}{ext}"
        provider_dir = FILES_DIR / str(provider_id)
        provider_dir.mkdir(parents=True, exist_ok=True)
        file_path = provider_dir / stored_filename
        file_path.write_bytes(content)

        # Create database record
        file_orm = await self.file_repo.create_file(
            provider_id=provider_id,
            filename=stored_filename,
            original_name=filename,
            file_type=self.get_safe_mime_type(ext),
            file_size=file_size,
            description=description,
            category=category,
        )

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PROVIDER_UPDATE,
                resource_type=ResourceType.PROVIDER,
                resource_id=provider_id,
                user=user,
                request=request,
                details={
                    "action": "file_upload",
                    "filename": filename,
                    "file_id": str(file_orm.id),
                },
            )

        await self.session.commit()
        return file_orm

    async def delete_file(
        self,
        provider_id: UUID,
        file_id: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> None:
        """Delete a provider file.

        Args:
            provider_id: Provider UUID
            file_id: File UUID
            user: Admin user deleting the file
            request: HTTP request for audit logging

        Raises:
            ValueError: If file not found
        """
        file_orm = await self.file_repo.get_by_provider_and_id(provider_id, file_id)
        if file_orm is None:
            raise ValueError("File not found")

        original_name = file_orm.original_name

        # Delete file from disk
        file_path = FILES_DIR / str(provider_id) / file_orm.filename
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError as e:
                log_warning(logger, "Failed to delete file from disk", e)

        # Delete from database
        await self.file_repo.delete_file(file_orm)

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PROVIDER_UPDATE,
                resource_type=ResourceType.PROVIDER,
                resource_id=provider_id,
                user=user,
                request=request,
                details={
                    "action": "file_delete",
                    "filename": original_name,
                    "file_id": str(file_id),
                },
            )

        await self.session.commit()

    def get_file_path(self, provider_id: UUID, filename: str) -> Path | None:
        """Get the file path for a provider file.

        Args:
            provider_id: Provider UUID
            filename: Stored filename

        Returns:
            Path to file or None if validation fails
        """
        file_path = FILES_DIR / str(provider_id) / filename
        if not self.validate_file_path(file_path, FILES_DIR):
            return None
        if not file_path.exists():
            return None
        return file_path
