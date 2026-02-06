"""Centralized validation constants for the licence API.

This module provides a single source of truth for all validation whitelists,
default values, and limits used across routers and services.
"""

from typing import Final

# =============================================================================
# License Constants
# =============================================================================

ALLOWED_LICENSE_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "active",
        "inactive",
        "suspended",
        "pending",
    }
)

ALLOWED_LICENSE_SORT_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "external_user_id",
        "synced_at",
        "status",
        "created_at",
        "employee_name",
        "provider_name",
        "is_external",
        "monthly_cost",
        "license_type",
    }
)

DEFAULT_LICENSE_SORT_COLUMN: Final[str] = "synced_at"

# =============================================================================
# Employee Constants
# =============================================================================

ALLOWED_EMPLOYEE_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "active",
        "offboarded",
        "pending",
        "on_leave",
    }
)

ALLOWED_EMPLOYEE_SOURCES: Final[frozenset[str]] = frozenset(
    {
        "hibob",
        "personio",
        "manual",
    }
)

ALLOWED_EMPLOYEE_SORT_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "full_name",
        "email",
        "department",
        "status",
        "source",
        "start_date",
        "termination_date",
        "synced_at",
        "license_count",
    }
)

DEFAULT_EMPLOYEE_SORT_COLUMN: Final[str] = "full_name"

# =============================================================================
# Service/Admin Account License Constants
# =============================================================================

ALLOWED_SERVICE_LICENSE_SORT_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "external_user_id",
        "synced_at",
        "created_at",
        "provider_name",
        "monthly_cost",
    }
)

ALLOWED_ADMIN_LICENSE_SORT_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "external_user_id",
        "synced_at",
        "created_at",
        "provider_name",
        "monthly_cost",
    }
)

DEFAULT_SERVICE_LICENSE_SORT_COLUMN: Final[str] = "external_user_id"

# =============================================================================
# Pagination Constants
# =============================================================================

DEFAULT_PAGE_SIZE: Final[int] = 50
MAX_PAGE_SIZE: Final[int] = 200
MAX_BULK_OPERATION_SIZE: Final[int] = 100
MAX_EXPORT_RECORDS: Final[int] = 10000

# =============================================================================
# Rate Limit Constants
# =============================================================================

SENSITIVE_OPERATION_LIMIT: Final[str] = "10/minute"
ADMIN_SENSITIVE_LIMIT: Final[str] = "5/minute"

# =============================================================================
# Password Constants
# =============================================================================

MIN_PASSWORD_LENGTH: Final[int] = 12
MAX_PASSWORD_LENGTH: Final[int] = 128

# =============================================================================
# Text Length Constants
# =============================================================================

MAX_SEARCH_LENGTH: Final[int] = 200
MAX_DEPARTMENT_LENGTH: Final[int] = 100
MAX_STATUS_LENGTH: Final[int] = 50
MAX_SORT_BY_LENGTH: Final[int] = 50
