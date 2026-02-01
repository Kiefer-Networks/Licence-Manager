"""CSRF protection middleware."""

import hmac
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from licence_api.security.csrf import verify_csrf_token


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
    EXEMPT_PATHS = frozenset({
        "/api/v1/auth/csrf-token",  # CSRF token endpoint
        "/api/v1/auth/login",  # Login needs CSRF but we handle it specially
        "/api/v1/auth/refresh",  # Token refresh uses httpOnly cookies for security
        "/health",  # Health check
    })

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
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"},
            )

        # Verify token signature and expiry
        if not verify_csrf_token(csrf_header):
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid or expired CSRF token"},
            )

        # Optional: Verify cookie matches header (double submit pattern)
        csrf_cookie = request.cookies.get("csrf_token")
        if csrf_cookie:
            # Extract token part from signed tokens for comparison
            header_token = csrf_header.split(":")[0] if ":" in csrf_header else csrf_header
            cookie_token = csrf_cookie.split(":")[0] if ":" in csrf_cookie else csrf_cookie
            if not hmac.compare_digest(header_token, cookie_token):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token mismatch"},
                )

        return await call_next(request)
