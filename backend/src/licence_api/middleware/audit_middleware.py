"""Audit logging middleware."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for audit logging of API requests."""

    # Methods that modify data
    AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Paths to exclude from audit logging
    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/google",
    }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process the request and log audit information.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from downstream handler
        """
        # Skip non-mutation methods and excluded paths
        if (
            request.method not in self.AUDIT_METHODS
            or request.url.path in self.EXCLUDED_PATHS
        ):
            return await call_next(request)

        # Extract client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Store in request state for use in routes
        request.state.client_ip = client_ip
        request.state.user_agent = user_agent

        # Process request
        response = await call_next(request)

        # Log the request (actual audit logging happens in services)
        if response.status_code < 400:
            logger.info(
                f"Audit: {request.method} {request.url.path} "
                f"status={response.status_code} ip={client_ip}"
            )
        else:
            logger.warning(
                f"Audit: {request.method} {request.url.path} "
                f"status={response.status_code} ip={client_ip}"
            )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Args:
            request: Incoming request

        Returns:
            Client IP address
        """
        # Check for forwarded headers (when behind proxy)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"
