"""API routers package."""

from licence_api.routers import auth, dashboard, licenses, providers, provider_import, reports, settings, users

__all__ = [
    "auth",
    "dashboard",
    "licenses",
    "providers",
    "provider_import",
    "reports",
    "settings",
    "users",
]
