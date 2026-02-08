"""Provider import router for CSV license imports."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.import_dto import (
    ImportExecuteRequest,
    ImportExecuteResponse,
    ImportJobStatus,
    ImportUploadResponse,
    ImportValidateRequest,
    ImportValidateResponse,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.import_service import ImportService

router = APIRouter()


def get_import_service(
    db: AsyncSession = Depends(get_db),
) -> ImportService:
    """Get ImportService instance."""
    return ImportService(db)


@router.get("/{provider_id}/import/template")
async def download_template(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_IMPORT))],
    service: Annotated[ImportService, Depends(get_import_service)],
    include_examples: bool = True,
) -> StreamingResponse:
    """Download CSV import template.

    Args:
        provider_id: Provider UUID
        current_user: Current authenticated user
        service: Import service instance
        include_examples: Whether to include example rows

    Returns:
        CSV file as StreamingResponse
    """
    import io

    content = await service.generate_template(provider_id, include_examples)

    # Create file-like object
    buffer = io.BytesIO(content.encode("utf-8-sig"))

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=license_import_template.csv"},
    )


@router.post("/{provider_id}/import/upload", response_model=ImportUploadResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def upload_import_file(
    request: Request,
    provider_id: UUID,
    file: UploadFile,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_IMPORT))],
    service: Annotated[ImportService, Depends(get_import_service)],
) -> ImportUploadResponse:
    """Upload a CSV file for import.

    The file will be analyzed and column mappings suggested.
    The upload ID returned should be used for subsequent validation and execution.

    Args:
        request: HTTP request (for rate limiting)
        provider_id: Provider UUID
        file: Uploaded CSV file
        current_user: Current authenticated user
        service: Import service instance

    Returns:
        ImportUploadResponse with file analysis and suggested mappings

    Raises:
        HTTPException: If file is invalid or provider not found
    """
    try:
        return await service.upload_file(
            provider_id=provider_id,
            file=file,
            user=current_user,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{provider_id}/import/validate", response_model=ImportValidateResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def validate_import(
    request: Request,
    provider_id: UUID,
    data: ImportValidateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_IMPORT))],
    service: Annotated[ImportService, Depends(get_import_service)],
) -> ImportValidateResponse:
    """Validate import data and get preview.

    Uses the previously uploaded file and validates each row
    according to the provided column mapping and options.

    Args:
        request: HTTP request (for rate limiting)
        provider_id: Provider UUID
        data: Validation request with column mapping
        current_user: Current authenticated user
        service: Import service instance

    Returns:
        ImportValidateResponse with validation results and preview

    Raises:
        HTTPException: If upload not found or validation fails
    """
    try:
        return await service.validate_import(
            provider_id=provider_id,
            request=data,
            user=current_user,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{provider_id}/import/execute", response_model=ImportExecuteResponse)
@limiter.limit("5/hour")
async def execute_import(
    request: Request,
    provider_id: UUID,
    data: ImportExecuteRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_IMPORT))],
    service: Annotated[ImportService, Depends(get_import_service)],
) -> ImportExecuteResponse:
    """Execute the import and create licenses.

    This will create licenses based on the validated data.
    Duplicates (licenses with existing external_user_id) will be skipped.

    Args:
        request: HTTP request (for rate limiting and audit)
        provider_id: Provider UUID
        data: Execution request with column mapping and options
        current_user: Current authenticated user
        service: Import service instance

    Returns:
        ImportExecuteResponse with job ID and status

    Raises:
        HTTPException: If import fails
    """
    try:
        return await service.execute_import(
            provider_id=provider_id,
            request=data,
            user=current_user,
            http_request=request,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{provider_id}/import/jobs/{job_id}", response_model=ImportJobStatus)
async def get_import_job_status(
    provider_id: UUID,
    job_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.LICENSES_VIEW))],
    service: Annotated[ImportService, Depends(get_import_service)],
) -> ImportJobStatus:
    """Get import job status.

    Args:
        provider_id: Provider UUID
        job_id: Import job UUID
        current_user: Current authenticated user
        service: Import service instance

    Returns:
        ImportJobStatus with job details and progress

    Raises:
        HTTPException: If job not found
    """
    result = await service.get_job_status(provider_id, job_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )
    return result
