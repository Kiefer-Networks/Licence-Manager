"""Backup router for system export and restore."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.backup import (
    BackupConfig,
    BackupConfigUpdate,
    BackupExportRequest,
    BackupInfoResponse,
    BackupListResponse,
    RestoreResponse,
    StoredBackup,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.csrf import CSRFProtected
from licence_api.security.rate_limit import (
    BACKUP_EXPORT_LIMIT,
    BACKUP_INFO_LIMIT,
    BACKUP_RESTORE_LIMIT,
    limiter,
)
from licence_api.services.backup_service import BackupService
from licence_api.utils.errors import raise_bad_request, raise_forbidden, raise_not_found

logger = logging.getLogger(__name__)

router = APIRouter()


class RestoreFromStoredRequest(BaseModel):
    """Request to restore from a stored backup."""

    password: str = Field(min_length=12, max_length=256)

# Maximum backup file size: 500MB
MAX_BACKUP_SIZE = 500 * 1024 * 1024

# Chunk size for streaming reads
READ_CHUNK_SIZE = 64 * 1024  # 64KB


async def read_upload_with_limit(
    file: UploadFile,
    max_size: int,
) -> bytes:
    """Read an uploaded file with size limit.

    Reads the file in chunks and stops early if the max size is exceeded,
    preventing memory exhaustion from oversized uploads.

    Args:
        file: The uploaded file
        max_size: Maximum allowed file size in bytes

    Returns:
        The file content as bytes

    Raises:
        HTTPException: If file exceeds max_size
    """
    chunks = []
    total_size = 0

    while True:
        chunk = await file.read(READ_CHUNK_SIZE)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {max_size // 1024 // 1024}MB",
            )
        chunks.append(chunk)

    return b"".join(chunks)


def get_backup_service(
    db: AsyncSession = Depends(get_db),
) -> BackupService:
    """Get BackupService instance."""
    return BackupService(db)


@router.post("/export")
@limiter.limit(BACKUP_EXPORT_LIMIT)
async def create_backup(
    request: Request,
    body: BackupExportRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SYSTEM_ADMIN))],
    service: Annotated[BackupService, Depends(get_backup_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> Response:
    """Create an encrypted backup of all system data.

    Requires system.admin permission.

    Returns encrypted backup file as application/octet-stream.
    """
    try:
        logger.info(f"Starting backup for user {current_user.email}")
        backup_data = await service.create_backup(
            password=body.password,
            user=current_user,
            request=request,
        )
        logger.info(f"Backup created successfully, size: {len(backup_data)} bytes")
    except (ValueError, KeyError, TypeError) as e:
        # Configuration or data format errors
        logger.error(f"Backup failed with ValueError/KeyError/TypeError: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backup configuration",
        )
    except OSError as e:
        # File system errors
        logger.error(f"Backup failed with OSError: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create backup due to storage error",
        )
    except Exception as e:
        # Generic fallback - don't expose internal details
        logger.error(f"Backup failed with unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create backup",
        )

    # Generate filename with timestamp
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
    filename = f"licence-backup-{timestamp}.lcbak"

    return Response(
        content=backup_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(backup_data)),
        },
    )


@router.post("/info", response_model=BackupInfoResponse)
@limiter.limit(BACKUP_INFO_LIMIT)
async def get_backup_info(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SYSTEM_ADMIN))],
    service: Annotated[BackupService, Depends(get_backup_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    file: UploadFile = File(...),
) -> BackupInfoResponse:
    """Get information about a backup file without decrypting.

    This endpoint validates the file format and returns basic info.
    Does not require the password.

    Requires system.admin permission.

    Note: CSRF protection is explicitly applied via CSRFProtected dependency.
    """
    # Validate file
    if file.filename is None:
        raise_bad_request("No filename provided")

    # Read file with streaming size check to prevent memory exhaustion
    content = await read_upload_with_limit(file, MAX_BACKUP_SIZE)

    if len(content) == 0:
        return BackupInfoResponse(
            valid_format=False,
            error="Empty file",
        )

    return service.get_backup_info(content)


# Rate limit for setup restore (stricter since no auth)
# Uses IP-based rate limiting via slowapi to prevent brute-force attacks
SETUP_RESTORE_LIMIT = "3/hour"


@router.post("/setup-restore", response_model=RestoreResponse)
@limiter.limit(SETUP_RESTORE_LIMIT)
async def setup_restore_backup(
    request: Request,
    service: Annotated[BackupService, Depends(get_backup_service)],
    file: UploadFile = File(...),
    password: str = Form(..., min_length=12, max_length=256),
) -> RestoreResponse:
    """Restore system from backup during initial setup.

    This endpoint is ONLY available when no admin users exist in the system.
    It allows restoring from a backup before creating the first admin account.

    WARNING: This deletes ALL existing data!

    Security measures:
    - Only works on fresh installations (no existing admin users)
    - Rate limited to 3 requests per hour per IP address
    - Requires minimum 12 character password (same as user passwords)
    - Backup file must be encrypted with AES-256-GCM

    No authentication required, but only works on fresh installations.
    """
    # Security check: Only allow if no admin users exist
    if await service.has_existing_admin_users():
        raise_forbidden("Setup restore is only available on fresh installations with no existing users")

    # Validate file
    if file.filename is None:
        raise_bad_request("No filename provided")

    if not file.filename.endswith(".lcbak"):
        raise_bad_request("Invalid file type. Expected .lcbak file")

    # Read file with streaming size check
    content = await read_upload_with_limit(file, MAX_BACKUP_SIZE)

    if len(content) == 0:
        raise_bad_request("Empty file")

    return await service.restore_backup(
        file_data=content,
        password=password,
        user=None,  # No user during setup
        request=request,
    )


# =============================================================================
# Scheduled Backup Endpoints
# =============================================================================


@router.get("/config", response_model=BackupConfig)
async def get_backup_config(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.BACKUPS_VIEW))],
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> BackupConfig:
    """Get backup configuration.

    Requires backups.view permission.
    """
    return await service.get_config()


@router.put("/config", response_model=BackupConfig)
@limiter.limit("10/minute")
async def update_backup_config(
    request: Request,
    body: BackupConfigUpdate,
    current_user: Annotated[
        AdminUser, Depends(require_permission(Permissions.BACKUPS_CONFIGURE))
    ],
    service: Annotated[BackupService, Depends(get_backup_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> BackupConfig:
    """Update backup configuration.

    Requires backups.configure permission.
    """
    try:
        return await service.update_config(
            request=body,
            user=current_user,
            http_request=request,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/list", response_model=BackupListResponse)
async def list_backups(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.BACKUPS_VIEW))],
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> BackupListResponse:
    """List all stored backups.

    Requires backups.view permission.
    """
    return await service.list_stored_backups()


@router.post("/trigger", response_model=StoredBackup)
@limiter.limit("5/hour")
async def trigger_backup(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.BACKUPS_CREATE))],
    service: Annotated[BackupService, Depends(get_backup_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> StoredBackup:
    """Trigger a manual backup.

    Creates a new backup using the configured encryption password.

    Requires backups.create permission.
    """
    try:
        result = await service.create_scheduled_backup()
        if result is None:
            raise_bad_request("Backup not configured. Please set an encryption password first.")
        return result
    except Exception as e:
        logger.error(f"Manual backup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create backup",
        )


@router.get("/{backup_id}/download")
@limiter.limit(BACKUP_INFO_LIMIT)
async def download_backup(
    request: Request,
    backup_id: str,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.BACKUPS_VIEW))],
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> Response:
    """Download a stored backup file.

    Requires backups.view permission.
    """
    try:
        file_data, filename = await service.get_stored_backup(backup_id)
        return Response(
            content=file_data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(file_data)),
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{backup_id}")
@limiter.limit("10/minute")
async def delete_backup(
    request: Request,
    backup_id: str,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.BACKUPS_DELETE))],
    service: Annotated[BackupService, Depends(get_backup_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> dict[str, str]:
    """Delete a stored backup.

    Requires backups.delete permission.
    """
    try:
        await service.delete_stored_backup(
            backup_id=backup_id,
            user=current_user,
            http_request=request,
        )
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{backup_id}/restore", response_model=RestoreResponse)
@limiter.limit(BACKUP_RESTORE_LIMIT)
async def restore_from_backup(
    request: Request,
    backup_id: str,
    body: RestoreFromStoredRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.BACKUPS_RESTORE))],
    service: Annotated[BackupService, Depends(get_backup_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> RestoreResponse:
    """Restore system from a stored backup.

    WARNING: This deletes ALL existing data!

    Requires backups.restore permission.
    """
    try:
        return await service.restore_from_stored(
            backup_id=backup_id,
            password=body.password,
            user=current_user,
            http_request=request,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
