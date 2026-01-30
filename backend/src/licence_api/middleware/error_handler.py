"""Global error handling middleware to prevent information disclosure."""

import logging
import os
import traceback
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from licence_api.config import get_settings

logger = logging.getLogger(__name__)


def _get_cors_headers(request: Request) -> dict[str, str]:
    """Get CORS headers for error responses.

    This ensures that error responses include proper CORS headers,
    which is necessary because exception handlers run before the
    CORS middleware can add headers to the response.

    Args:
        request: The incoming request

    Returns:
        Dict of CORS headers to add to the response
    """
    origin = request.headers.get("origin")
    if not origin:
        return {}

    # Get allowed origins from environment or use development default
    settings = get_settings()
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    if not cors_origins_env and settings.environment == "development":
        cors_origins_env = "http://localhost:3000"

    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

    # Only add CORS headers if the origin is allowed
    if origin in allowed_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }

    return {}

# Safe error messages that can be shown to users
SAFE_ERROR_MESSAGES = {
    400: "Invalid request",
    401: "Authentication required",
    403: "Access denied",
    404: "Resource not found",
    405: "Method not allowed",
    409: "Conflict with existing resource",
    422: "Invalid input data",
    429: "Too many requests",
    500: "Internal server error",
    502: "Service unavailable",
    503: "Service temporarily unavailable",
}

# Error messages that are safe to pass through
# These don't reveal internal implementation details
ALLOWED_ERROR_PATTERNS = [
    "Invalid credentials",
    "Authentication required",
    "Access denied",
    "Insufficient permissions",
    "Insufficient role",
    "Superadmin access required",
    "Admin access required",
    "Resource not found",
    "User not found",
    "Employee not found",
    "Provider not found",
    "License not found",
    "Role not found",
    "Permission not found",
    "Session not found",
    "Account is disabled",
    "Account is locked",
    "Password change not available",
    "Current password is incorrect",
    "Password was recently used",
    "Refresh token required",
    "Invalid refresh token",
    "Refresh token expired",
    "Invalid or expired token",
    "Invalid token type",
    "CSRF token missing",
    "Invalid or expired CSRF token",
    "CSRF token mismatch",
    "Invalid Google token",
    "Token was not issued for this application",
    "Email domain not allowed",
    "Email already registered",
    "Role code already exists",
    "Cannot delete system role",
    "Cannot modify system role permissions",
    "File too large",
    "Invalid file type",
    "Upload failed",
]


def is_safe_error_message(message: str) -> bool:
    """Check if an error message is safe to expose to users.

    Args:
        message: Error message to check

    Returns:
        True if message is safe to expose
    """
    message_lower = message.lower()
    for pattern in ALLOWED_ERROR_PATTERNS:
        if pattern.lower() in message_lower:
            return True
    return False


def sanitize_error_detail(detail: Any, status_code: int) -> str:
    """Sanitize error detail to prevent information disclosure.

    Args:
        detail: Original error detail
        status_code: HTTP status code

    Returns:
        Safe error message
    """
    if isinstance(detail, str):
        if is_safe_error_message(detail):
            return detail
    elif isinstance(detail, list):
        # Validation errors - extract safe field information
        safe_errors = []
        for error in detail:
            if isinstance(error, dict):
                loc = error.get("loc", [])
                msg = error.get("msg", "Invalid value")
                # Only include field name, not detailed type information
                field = loc[-1] if loc else "field"
                if isinstance(field, str) and not field.startswith("_"):
                    safe_errors.append(f"{field}: {msg}")
        if safe_errors:
            return "; ".join(safe_errors[:3])  # Limit to 3 errors

    # Return generic message for unknown patterns
    return SAFE_ERROR_MESSAGES.get(status_code, "Request failed")


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with sanitized messages.

    Args:
        request: FastAPI request
        exc: HTTP exception

    Returns:
        JSONResponse with sanitized error
    """
    settings = get_settings()
    cors_headers = _get_cors_headers(request)

    # In debug mode, return original detail
    if settings.debug:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=cors_headers,
        )

    # Sanitize error message
    safe_detail = sanitize_error_detail(exc.detail, exc.status_code)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": safe_detail},
        headers=cors_headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation exceptions with sanitized messages.

    Args:
        request: FastAPI request
        exc: Validation exception

    Returns:
        JSONResponse with sanitized error
    """
    settings = get_settings()
    cors_headers = _get_cors_headers(request)

    # Log the full error for debugging
    logger.warning(f"Validation error for {request.url}: {exc.errors()}")

    # In debug mode, return full details
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
            headers=cors_headers,
        )

    # Sanitize validation errors
    safe_detail = sanitize_error_detail(exc.errors(), status.HTTP_422_UNPROCESSABLE_ENTITY)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": safe_detail},
        headers=cors_headers,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions without leaking information.

    Args:
        request: FastAPI request
        exc: Unexpected exception

    Returns:
        JSONResponse with generic error
    """
    settings = get_settings()
    cors_headers = _get_cors_headers(request)

    # Log the full error for debugging
    logger.error(f"Unhandled exception for {request.url}: {exc}", exc_info=True)

    # In debug mode, return more details
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
            },
            headers=cors_headers,
        )

    # Return generic error message
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": SAFE_ERROR_MESSAGES[500]},
        headers=cors_headers,
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy exceptions without leaking database details.

    Args:
        request: FastAPI request
        exc: SQLAlchemy exception

    Returns:
        JSONResponse with safe error
    """
    settings = get_settings()
    cors_headers = _get_cors_headers(request)

    # Log the full error for debugging
    logger.error(f"Database error for {request.url}: {exc}", exc_info=True)

    # Check for integrity errors (duplicates, foreign key violations)
    if isinstance(exc, IntegrityError):
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": "Resource already exists"},
                headers=cors_headers,
            )
        if "foreign key" in str(exc).lower():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Referenced resource not found"},
                headers=cors_headers,
            )

    # In debug mode, return more details
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Database error",
                "type": type(exc).__name__,
            },
            headers=cors_headers,
        )

    # Return generic error message
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred"},
        headers=cors_headers,
    )
