"""Centralized HTTP error helpers for routers.

These functions provide consistent error responses across all routers.
"""

from typing import Any, NoReturn
from uuid import UUID

from fastapi import HTTPException, Request, status

from licence_api.middleware.error_handler import sanitize_error_for_audit


async def log_sync_connection_error(
    audit_service: Any,
    provider_id: UUID | None,
    current_user: Any,
    request: Request,
    exception: Exception,
) -> dict[str, Any]:
    """Log a sync connection error to audit trail.

    Args:
        audit_service: AuditService instance
        provider_id: Provider UUID (optional for all-provider sync)
        current_user: Current authenticated user
        request: FastAPI request object
        exception: The caught exception

    Returns:
        Error details dict for the response
    """
    from licence_api.services.audit_service import AuditAction, ResourceType

    await audit_service.log(
        action=AuditAction.PROVIDER_SYNC,
        resource_type=ResourceType.PROVIDER,
        resource_id=provider_id,
        user=current_user,
        request=request,
        details={
            "success": False,
            "error_code": "CONNECTION_ERROR",
            "error_type": type(exception).__name__,
        },
    )
    return {"error": "Connection to provider failed"}


async def log_sync_unexpected_error(
    audit_service: Any,
    provider_id: UUID | None,
    current_user: Any,
    request: Request,
    exception: Exception,
) -> dict[str, Any]:
    """Log an unexpected sync error to audit trail.

    Args:
        audit_service: AuditService instance
        provider_id: Provider UUID (optional for all-provider sync)
        current_user: Current authenticated user
        request: FastAPI request object
        exception: The caught exception

    Returns:
        Error details dict for the response
    """
    from licence_api.services.audit_service import AuditAction, ResourceType

    await audit_service.log(
        action=AuditAction.PROVIDER_SYNC,
        resource_type=ResourceType.PROVIDER,
        resource_id=provider_id,
        user=current_user,
        request=request,
        details={"success": False, **sanitize_error_for_audit(exception)},
    )
    return {"error": "Sync operation failed"}


def raise_not_found(entity: str = "Resource") -> NoReturn:
    """Raise a 404 Not Found error.

    Args:
        entity: The name of the entity that was not found (e.g., "License", "User")

    Raises:
        HTTPException: With 404 status code
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} not found",
    )


def raise_bad_request(message: str = "Invalid request") -> NoReturn:
    """Raise a 400 Bad Request error.

    Args:
        message: The error message to return

    Raises:
        HTTPException: With 400 status code
    """
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
    )


def raise_conflict(message: str = "Resource already exists") -> NoReturn:
    """Raise a 409 Conflict error.

    Args:
        message: The error message to return

    Raises:
        HTTPException: With 409 status code
    """
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=message,
    )


def raise_forbidden(message: str = "Access denied") -> NoReturn:
    """Raise a 403 Forbidden error.

    Args:
        message: The error message to return

    Raises:
        HTTPException: With 403 status code
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message,
    )


def handle_value_error_as_not_found(entity: str = "Resource") -> NoReturn:
    """Helper to convert ValueError to 404 HTTPException.

    Args:
        entity: The name of the entity that was not found

    Raises:
        HTTPException: With 404 status code
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} not found",
    )
