"""CORS logging middleware for security monitoring."""

import logging
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class CORSLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log rejected CORS origins for security monitoring.

    This middleware checks incoming requests for Origin headers and logs
    when a request is received from an origin that is not in the allowed
    list. This helps detect potential cross-origin attack attempts or
    misconfigured clients.

    Should be added AFTER CORSMiddleware so it runs BEFORE it on requests.
    """

    def __init__(self, app, allowed_origins: list[str]) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application
            allowed_origins: List of allowed origin URLs
        """
        super().__init__(app)
        self.allowed_origins = frozenset(allowed_origins)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process the request and log rejected origins.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from downstream handler
        """
        origin = request.headers.get("origin")

        if origin and origin not in self.allowed_origins:
            # Log rejected CORS origin for security monitoring
            logger.warning(
                "CORS origin rejected",
                extra={
                    "origin": origin,
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                    "user_agent": request.headers.get("user-agent", "unknown"),
                },
            )

        return await call_next(request)
