"""Domain-specific exceptions for the licence API.

These exceptions provide a clean separation between service-layer errors
and HTTP responses, avoiding string matching in routers.
"""

from typing import Any


class LicenceAPIError(Exception):
    """Base exception for all licence API errors."""

    def __init__(self, message: str = "An error occurred", details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# =============================================================================
# Resource Not Found Errors (404)
# =============================================================================


class NotFoundError(LicenceAPIError):
    """Base class for resource not found errors."""

    pass


class UserNotFoundError(NotFoundError):
    """Raised when a user cannot be found."""

    def __init__(self, user_id: str | None = None) -> None:
        message = "User not found"
        details = {"user_id": str(user_id)} if user_id else {}
        super().__init__(message, details)


class RoleNotFoundError(NotFoundError):
    """Raised when a role cannot be found."""

    def __init__(self, role_id: str | None = None, role_code: str | None = None) -> None:
        message = "Role not found"
        details: dict[str, Any] = {}
        if role_id:
            details["role_id"] = str(role_id)
        if role_code:
            details["role_code"] = role_code
        super().__init__(message, details)


# =============================================================================
# Conflict Errors (409)
# =============================================================================


class ConflictError(LicenceAPIError):
    """Base class for resource conflict errors."""

    pass


class UserAlreadyExistsError(ConflictError):
    """Raised when trying to create a user that already exists."""

    def __init__(self, email: str | None = None) -> None:
        message = "User with this email already exists"
        details = {"email": email} if email else {}
        super().__init__(message, details)


class RoleAlreadyExistsError(ConflictError):
    """Raised when trying to create a role that already exists."""

    def __init__(self, code: str | None = None) -> None:
        message = "Role with this code already exists"
        details = {"code": code} if code else {}
        super().__init__(message, details)


# =============================================================================
# Validation Errors (400)
# =============================================================================


class ValidationError(LicenceAPIError):
    """Base class for validation errors."""

    pass


# =============================================================================
# Permission Errors (403)
# =============================================================================


class CannotDeleteSelfError(LicenceAPIError):
    """Raised when user tries to delete themselves."""

    def __init__(self) -> None:
        super().__init__("Cannot delete your own account")


class CannotModifySystemRoleError(LicenceAPIError):
    """Raised when trying to modify a system role."""

    def __init__(self, role_code: str | None = None) -> None:
        message = "Cannot modify system role"
        details = {"role_code": role_code} if role_code else {}
        super().__init__(message, details)
