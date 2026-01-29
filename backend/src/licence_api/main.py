"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from licence_api.config import get_settings
from licence_api.middleware.audit_middleware import AuditMiddleware
from licence_api.routers import auth, dashboard, licenses, manual_licenses, payment_methods, provider_files, providers, reports, settings, users
from licence_api.tasks.scheduler import start_scheduler, stop_scheduler


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, max-age=0"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    await start_scheduler()
    yield
    # Shutdown
    await stop_scheduler()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_settings()

    app = FastAPI(
        title=config.app_name,
        version="0.1.0",
        description="License Management System API",
        lifespan=lifespan,
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None,
    )

    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS middleware - configure allowed origins from environment
    allowed_origins = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000"
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )

    # Audit middleware
    app.add_middleware(AuditMiddleware)

    # Include routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(providers.router, prefix="/api/v1/providers", tags=["Providers"])
    app.include_router(provider_files.router, prefix="/api/v1/providers", tags=["Provider Files"])
    app.include_router(licenses.router, prefix="/api/v1/licenses", tags=["Licenses"])
    app.include_router(manual_licenses.router, prefix="/api/v1/manual-licenses", tags=["Manual Licenses"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
    app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
    app.include_router(payment_methods.router, prefix="/api/v1/payment-methods", tags=["Payment Methods"])

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()
