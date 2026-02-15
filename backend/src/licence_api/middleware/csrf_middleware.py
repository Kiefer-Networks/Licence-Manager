"""CSRF protection middleware."""

import hmac

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from licence_api.security.csrf import CSRF_TOKEN_DELIMITER, verify_csrf_token


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to validate CSRF tokens for state-changing requests.

    This implements the Double Submit Cookie pattern:
    1. Server sets a CSRF token in a readable cookie
    2. Client must include the same token in X-CSRF-Token header
    3. Server validates both match and signature is valid

    Exempt paths can be configured for endpoints that don't need CSRF
    (e.g., login endpoint gets CSRF token first).
    """

    # Paths that are exempt from CSRF validation (exact match only)
    EXEMPT_PATHS = frozenset(
        {
            "/api/v1/auth/csrf-token",  # CSRF token endpoint
            "/api/v1/auth/login",  # Login needs CSRF but we handle it specially
            "/api/v1/auth/refresh",  # Token refresh uses httpOnly cookies for security
            "/api/v1/backup/setup-restore",  # Setup restore is unauthenticated
            "/health",  # Health check
        }
    )

    # Safe HTTP methods that don't require CSRF validation
    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

    async def dispatch(self, request: Request, call_next):
        """Process request and validate CSRF if needed."""
        # Skip CSRF for safe methods
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        # Skip CSRF for exempt paths (exact match only to prevent path traversal)
        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Get CSRF token from header
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_header:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing",
            )

        # Verify token signature and expiry
        if not verify_csrf_token(csrf_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired CSRF token",
            )

        # Optional: Verify cookie matches header (double submit pattern)
        csrf_cookie = request.cookies.get("csrf_token")
        if csrf_cookie:
            # Extract token part (first component) from signed tokens for comparison
            if CSRF_TOKEN_DELIMITER in csrf_header:
                header_token = csrf_header.split(CSRF_TOKEN_DELIMITER)[0]
            else:
                header_token = csrf_header
            if CSRF_TOKEN_DELIMITER in csrf_cookie:
                cookie_token = csrf_cookie.split(CSRF_TOKEN_DELIMITER)[0]
            else:
                cookie_token = csrf_cookie
            if not hmac.compare_digest(header_token, cookie_token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token mismatch",
                )

        return await call_next(request)
