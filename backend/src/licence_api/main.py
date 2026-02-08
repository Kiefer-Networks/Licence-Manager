"""FastAPI application entry point."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from licence_api.config import get_settings
from licence_api.middleware.audit_middleware import AuditMiddleware
from licence_api.middleware.cors_logging_middleware import CORSLoggingMiddleware
from licence_api.middleware.csrf_middleware import CSRFMiddleware
from licence_api.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler,
)
from licence_api.routers import (
    admin_accounts,
    audit,
    auth,
    backup,
    cancellation,
    dashboard,
    email_settings,
    exports,
    external_accounts,
    license_packages,
    licenses,
    manual_licenses,
    organization_licenses,
    payment_methods,
    provider_files,
    provider_import,
    providers,
    rbac,
    reports,
    service_accounts,
    settings,
    users,
)
from licence_api.security.rate_limit import limiter
from licence_api.services.permission_sync_service import sync_system_role_permissions
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
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        # Strict Transport Security (HSTS) - only in production
        if not get_settings().debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    # Sync system role permissions (adds new permissions to admin/auditor roles)
    await sync_system_role_permissions()
    await start_scheduler()
    yield
    # Shutdown
    await stop_scheduler()

    # Close shared HTTP clients to release connections
    from licence_api.providers.slack import SlackProvider
    from licence_api.services.notification_service import NotificationService

    await NotificationService.close_client()
    await SlackProvider.close_client()


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

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Security: Sanitized error handlers to prevent information disclosure
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # CORS origins configuration
    # Security: Validate origins and reject wildcards when credentials are enabled
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")

    # In production, CORS_ORIGINS must be explicitly configured
    if config.environment == "production" and not cors_origins_env:
        raise ValueError(
            "CORS_ORIGINS environment variable must be set in production. "
            "Example: CORS_ORIGINS=https://app.example.com,https://admin.example.com"
        )

    # Default to localhost only in development
    if not cors_origins_env and config.environment == "development":
        cors_origins_env = "http://localhost:3000"

    raw_origins = cors_origins_env.split(",") if cors_origins_env else []
    allowed_origins = []
    for origin in raw_origins:
        origin = origin.strip()
        # Reject wildcard origins when credentials are enabled (security requirement)
        if origin == "*":
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' wildcard when allow_credentials=True. "
                "Specify explicit origins."
            )
        # Validate origin format (must be scheme://host[:port])
        if origin and (origin.startswith("http://") or origin.startswith("https://")):
            allowed_origins.append(origin)

    if not allowed_origins and config.environment != "production":
        allowed_origins = ["http://localhost:3000"]

    # Middleware order matters! FastAPI processes middleware in REVERSE order of addition.
    # So we add them in this order: SecurityHeaders -> Audit -> CSRF -> CORS
    # This means CORS runs FIRST on requests (handles preflight), then CSRF, then Audit.

    # Security headers middleware (runs last on request, first on response)
    app.add_middleware(SecurityHeadersMiddleware)

    # Session middleware for OAuth state (uses JWT secret for signing)
    app.add_middleware(SessionMiddleware, secret_key=config.jwt_secret)

    # Audit middleware (runs after CSRF on request)
    app.add_middleware(AuditMiddleware)

    # CSRF protection middleware (runs after CORS on request)
    app.add_middleware(CSRFMiddleware)

    # CORS middleware - MUST be added last so it runs FIRST on incoming requests
    # This is critical for handling OPTIONS preflight requests before other middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-CSRF-Token"],
    )

    # CORS logging middleware - logs rejected origins for security monitoring
    # Added after CORSMiddleware so it runs BEFORE it on incoming requests
    app.add_middleware(CORSLoggingMiddleware, allowed_origins=allowed_origins)

    # Include routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(rbac.router, prefix="/api/v1/rbac", tags=["RBAC"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(providers.router, prefix="/api/v1/providers", tags=["Providers"])
    app.include_router(provider_files.router, prefix="/api/v1/providers", tags=["Provider Files"])
    app.include_router(provider_import.router, prefix="/api/v1/providers", tags=["Provider Import"])
    app.include_router(
        license_packages.router, prefix="/api/v1/providers", tags=["License Packages"]
    )
    app.include_router(
        organization_licenses.router,
        prefix="/api/v1/providers",
        tags=["Organization Licenses"],
    )
    app.include_router(licenses.router, prefix="/api/v1/licenses", tags=["Licenses"])
    app.include_router(
        service_accounts.router,
        prefix="/api/v1/service-accounts",
        tags=["Service Accounts"],
    )
    app.include_router(
        admin_accounts.router,
        prefix="/api/v1/admin-accounts",
        tags=["Admin Accounts"],
    )
    app.include_router(
        manual_licenses.router,
        prefix="/api/v1/manual-licenses",
        tags=["Manual Licenses"],
    )
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
    app.include_router(cancellation.router, prefix="/api/v1", tags=["Cancellation"])
    # Email settings must be registered before generic settings to avoid route conflict
    app.include_router(
        email_settings.router,
        prefix="/api/v1/settings/email",
        tags=["Email Settings"],
    )
    app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
    app.include_router(
        payment_methods.router,
        prefix="/api/v1/payment-methods",
        tags=["Payment Methods"],
    )
    app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
    app.include_router(exports.router, prefix="/api/v1/exports", tags=["Exports"])
    app.include_router(backup.router, prefix="/api/v1/backup", tags=["Backup"])
    app.include_router(external_accounts.router, prefix="/api/v1", tags=["External Accounts"])

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()
