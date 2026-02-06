"""Authentication middleware."""

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from licence_api.utils.request_id import generate_request_id


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication handling.

    Note: Most auth is handled via FastAPI dependencies.
    This middleware is for additional cross-cutting concerns.
    """

    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/google",
        "/api/v1/settings/status",
    }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process the request.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from downstream handler
        """
        # Add request ID for tracing
        request.state.request_id = generate_request_id()

        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request.state.request_id

        return response
