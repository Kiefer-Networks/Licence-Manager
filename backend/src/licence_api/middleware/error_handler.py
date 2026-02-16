"""Global error handling middleware to prevent information disclosure.

Error responses follow RFC 7807 (Problem Details for HTTP APIs).
"""

import logging
import os
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from licence_api.config import get_settings

# RFC 7807 Content-Type header
PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(__name__)

# RFC 7807 error type URIs mapped to status codes
ERROR_TYPE_MAP = {
    400: "https://datatracker.ietf.org/doc/html/rfc7231#section-6.5.1",
    401: "https://datatracker.ietf.org/doc/html/rfc7235#section-3.1",
    403: "https://datatracker.ietf.org/doc/html/rfc7231#section-6.5.3",
    404: "https://datatracker.ietf.org/doc/html/rfc7231#section-6.5.4",
    405: "https://datatracker.ietf.org/doc/html/rfc7231#section-6.5.5",
    409: "https://datatracker.ietf.org/doc/html/rfc7231#section-6.5.8",
    422: "https://datatracker.ietf.org/doc/html/rfc4918#section-11.2",
    429: "https://datatracker.ietf.org/doc/html/rfc6585#section-4",
    500: "https://datatracker.ietf.org/doc/html/rfc7231#section-6.6.1",
    502: "https://datatracker.ietf.org/doc/html/rfc7231#section-6.6.3",
    503: "https://datatracker.ietf.org/doc/html/rfc7231#section-6.6.4",
}


def _problem_response(
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    cors_headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Create an RFC 7807 Problem Details JSON response.

    See: https://datatracker.ietf.org/doc/html/rfc7807

    Args:
        request: The incoming request
        status_code: HTTP status code
        title: Short human-readable summary of the problem type
        detail: Human-readable explanation specific to this occurrence
        cors_headers: Optional CORS headers

    Returns:
        JSONResponse with application/problem+json content type
    """
    headers = dict(cors_headers or {})
    headers["Content-Type"] = PROBLEM_JSON_MEDIA_TYPE

    body: dict[str, Any] = {
        "type": ERROR_TYPE_MAP.get(status_code, "about:blank"),
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": str(request.url.path),
    }

    return JSONResponse(
        status_code=status_code,
        content=body,
        headers=headers,
    )


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
    "Audit log not found",
    "Pattern not found",
    "External account not found",
    "Avatar not found",
    "SMTP configuration not found",
    "Backup not found",
    "Google OAuth is not configured",
    "Invalid pattern configuration",
    "Invalid employee data",
    "Failed to link external account",
    "Backup operation failed",
    "Invalid backup configuration",
    "Failed to create backup",
    "No filename provided",
    "Backup not configured",
    "Setup restore is only available",
    "Unknown event type",
    "No employee linked",
    "Employee not found or cannot be deleted",
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
    """Handle HTTP exceptions with sanitized messages per RFC 7807.

    Args:
        request: FastAPI request
        exc: HTTP exception

    Returns:
        JSONResponse with RFC 7807 Problem Details
    """
    settings = get_settings()
    cors_headers = _get_cors_headers(request)
    # Preserve exception headers (e.g., WWW-Authenticate)
    if exc.headers:
        cors_headers = {**cors_headers, **exc.headers}
    title = SAFE_ERROR_MESSAGES.get(exc.status_code, "Request failed")

    # In debug mode, return original detail
    if settings.debug:
        return _problem_response(request, exc.status_code, title, str(exc.detail), cors_headers)

    # Sanitize error message
    safe_detail = sanitize_error_detail(exc.detail, exc.status_code)

    return _problem_response(request, exc.status_code, title, safe_detail, cors_headers)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation exceptions with sanitized messages per RFC 7807.

    Args:
        request: FastAPI request
        exc: Validation exception

    Returns:
        JSONResponse with RFC 7807 Problem Details
    """
    settings = get_settings()
    cors_headers = _get_cors_headers(request)
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    title = "Invalid input data"

    # Log the full error for debugging
    logger.warning(f"Validation error for {request.url}: {exc.errors()}")

    # In debug mode, return full details
    if settings.debug:
        return _problem_response(
            request, status_code, title, str(exc.errors()), cors_headers
        )

    # Sanitize validation errors
    safe_detail = sanitize_error_detail(exc.errors(), status_code)

    return _problem_response(request, status_code, title, safe_detail, cors_headers)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions without leaking information per RFC 7807.

    Args:
        request: FastAPI request
        exc: Unexpected exception

    Returns:
        JSONResponse with RFC 7807 Problem Details
    """
    settings = get_settings()
    cors_headers = _get_cors_headers(request)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    title = SAFE_ERROR_MESSAGES[500]

    # Log the full error for debugging
    logger.error(f"Unhandled exception for {request.url}: {exc}", exc_info=True)

    # In debug mode, return more details
    if settings.debug:
        return _problem_response(request, status_code, title, str(exc), cors_headers)

    # Return generic error message
    return _problem_response(request, status_code, title, title, cors_headers)


def sanitize_error_for_audit(error: Exception) -> dict[str, str]:
    """Sanitize exception information for audit log storage.

    This function removes potentially sensitive details from exceptions
    before storing them in audit logs. It avoids exposing:
    - File system paths
    - Database connection strings
    - Stack traces
    - Internal module names

    Args:
        error: The exception to sanitize

    Returns:
        Dict with 'error_type' and 'error_code' keys
    """
    import re

    error_type = type(error).__name__

    # Map exception types to safe error codes
    error_code_map = {
        "ConnectionError": "CONNECTION_FAILED",
        "TimeoutError": "TIMEOUT",
        "ValueError": "INVALID_VALUE",
        "KeyError": "MISSING_KEY",
        "TypeError": "TYPE_ERROR",
        "AttributeError": "ATTRIBUTE_ERROR",
        "PermissionError": "PERMISSION_DENIED",
        "FileNotFoundError": "FILE_NOT_FOUND",
        "IOError": "IO_ERROR",
        "OSError": "OS_ERROR",
        "HTTPException": "HTTP_ERROR",
        "IntegrityError": "DATABASE_INTEGRITY_ERROR",
        "OperationalError": "DATABASE_OPERATION_ERROR",
        "ProgrammingError": "DATABASE_PROGRAMMING_ERROR",
    }

    error_code = error_code_map.get(error_type, "UNKNOWN_ERROR")

    # For safe error types, include a sanitized message (no paths, no secrets)
    error_msg = str(error)

    # Remove file paths (Unix and Windows)
    error_msg = re.sub(r"['\"]?(/[a-zA-Z0-9_./\-]+|[A-Z]:\\[^\s'\"]+)['\"]?", "[PATH]", error_msg)

    # Remove anything that looks like a connection string
    conn_pattern = r"(postgresql|mysql|sqlite|mongodb|redis)://[^\s]+"
    error_msg = re.sub(conn_pattern, "[CONNECTION_STRING]", error_msg)

    # Remove email addresses
    error_msg = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL]", error_msg)

    # Truncate long messages
    if len(error_msg) > 100:
        error_msg = error_msg[:97] + "..."

    return {
        "error_type": error_type,
        "error_code": error_code,
        "error_summary": error_msg,
    }


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
            return _problem_response(
                request,
                status.HTTP_409_CONFLICT,
                "Conflict with existing resource",
                "Resource already exists",
                cors_headers,
            )
        if "foreign key" in str(exc).lower():
            return _problem_response(
                request,
                status.HTTP_400_BAD_REQUEST,
                "Invalid request",
                "Referenced resource not found",
                cors_headers,
            )

    # In debug mode, return more details
    if settings.debug:
        return _problem_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Database error",
            type(exc).__name__,
            cors_headers,
        )

    # Return generic error message
    return _problem_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Database error",
        "Database error occurred",
        cors_headers,
    )
