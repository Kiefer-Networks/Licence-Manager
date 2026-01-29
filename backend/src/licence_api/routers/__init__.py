"""API routers package."""

from licence_api.routers import auth, dashboard, licenses, providers, reports, settings, users

__all__ = [
    "auth",
    "dashboard",
    "licenses",
    "providers",
    "reports",
    "settings",
    "users",
]
