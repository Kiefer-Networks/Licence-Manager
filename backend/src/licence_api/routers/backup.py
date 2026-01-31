"""Backup router for system export and restore."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.backup import (
    BackupExportRequest,
    BackupInfoResponse,
    RestoreResponse,
)
from licence_api.security.auth import require_permission, Permissions
from licence_api.security.rate_limit import limiter
from licence_api.services.backup_service import BackupService

router = APIRouter()

# Maximum backup file size: 500MB
MAX_BACKUP_SIZE = 500 * 1024 * 1024

# Rate limits for backup operations
BACKUP_EXPORT_LIMIT = "2/hour"
BACKUP_RESTORE_LIMIT = "2/hour"
BACKUP_INFO_LIMIT = "10/minute"


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
) -> Response:
    """Create an encrypted backup of all system data.

    Requires system.admin permission.

    Returns encrypted backup file as application/octet-stream.
    """
    try:
        backup_data = await service.create_backup(
            password=body.password,
            user=current_user,
            request=request,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}",
        )

    # Generate filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    filename = f"licence-backup-{timestamp}.lcbak"

    return Response(
        content=backup_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(backup_data)),
        },
    )


@router.post("/restore", response_model=RestoreResponse)
@limiter.limit(BACKUP_RESTORE_LIMIT)
async def restore_backup(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SYSTEM_ADMIN))],
    service: Annotated[BackupService, Depends(get_backup_service)],
    file: UploadFile = File(...),
    password: str = Form(..., min_length=8),
) -> RestoreResponse:
    """Restore system from an encrypted backup.

    WARNING: This deletes ALL existing data!

    Requires system.admin permission.

    Args:
        file: Encrypted backup file (.lcbak)
        password: Password for decryption
    """
    # Validate file
    if file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    if not file.filename.endswith(".lcbak"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Expected .lcbak file",
        )

    # Read file content
    content = await file.read()

    if len(content) > MAX_BACKUP_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_BACKUP_SIZE // 1024 // 1024}MB",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    return await service.restore_backup(
        file_data=content,
        password=password,
        user=current_user,
        request=request,
    )


@router.post("/info", response_model=BackupInfoResponse)
@limiter.limit(BACKUP_INFO_LIMIT)
async def get_backup_info(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SYSTEM_ADMIN))],
    file: UploadFile = File(...),
) -> BackupInfoResponse:
    """Get information about a backup file without decrypting.

    This endpoint validates the file format and returns basic info.
    Does not require the password.

    Requires system.admin permission.
    """
    # Validate file
    if file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    # Read file content
    content = await file.read()

    if len(content) > MAX_BACKUP_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_BACKUP_SIZE // 1024 // 1024}MB",
        )

    if len(content) == 0:
        return BackupInfoResponse(
            valid_format=False,
            error="Empty file",
        )

    # Note: BackupService doesn't need a session for get_backup_info
    # but we create one for consistency
    service = BackupService(None)  # type: ignore
    return service.get_backup_info(content)
