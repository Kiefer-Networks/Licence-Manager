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


class ProviderNotFoundError(NotFoundError):
    """Raised when a provider cannot be found."""

    def __init__(self, provider_id: str | None = None) -> None:
        message = "Provider not found"
        details = {"provider_id": str(provider_id)} if provider_id else {}
        super().__init__(message, details)


class LicenseNotFoundError(NotFoundError):
    """Raised when a license cannot be found."""

    def __init__(self, license_id: str | None = None) -> None:
        message = "License not found"
        details = {"license_id": str(license_id)} if license_id else {}
        super().__init__(message, details)


class LicensePackageNotFoundError(NotFoundError):
    """Raised when a license package cannot be found."""

    def __init__(self, package_id: str | None = None) -> None:
        message = "License package not found"
        details = {"package_id": str(package_id)} if package_id else {}
        super().__init__(message, details)


class EmployeeNotFoundError(NotFoundError):
    """Raised when an employee cannot be found."""

    def __init__(self, employee_id: str | None = None) -> None:
        message = "Employee not found"
        details = {"employee_id": str(employee_id)} if employee_id else {}
        super().__init__(message, details)


class FileNotFoundError(NotFoundError):
    """Raised when a file cannot be found."""

    def __init__(self, file_id: str | None = None) -> None:
        message = "File not found"
        details = {"file_id": str(file_id)} if file_id else {}
        super().__init__(message, details)


class PaymentMethodNotFoundError(NotFoundError):
    """Raised when a payment method cannot be found."""

    def __init__(self, payment_method_id: str | None = None) -> None:
        message = "Payment method not found"
        details = {"payment_method_id": str(payment_method_id)} if payment_method_id else {}
        super().__init__(message, details)


class PatternNotFoundError(NotFoundError):
    """Raised when a service/admin account pattern cannot be found."""

    def __init__(self, pattern_id: str | None = None) -> None:
        message = "Pattern not found"
        details = {"pattern_id": str(pattern_id)} if pattern_id else {}
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


class ProviderAlreadyExistsError(ConflictError):
    """Raised when trying to create a provider that already exists."""

    def __init__(self, name: str | None = None) -> None:
        message = "Provider with this name already exists"
        details = {"name": name} if name else {}
        super().__init__(message, details)


class PatternAlreadyExistsError(ConflictError):
    """Raised when trying to create a pattern that already exists."""

    def __init__(self, pattern: str | None = None) -> None:
        message = "Pattern already exists"
        details = {"pattern": pattern} if pattern else {}
        super().__init__(message, details)


# =============================================================================
# Validation Errors (400)
# =============================================================================


class ValidationError(LicenceAPIError):
    """Base class for validation errors."""

    pass


class InvalidCredentialsError(ValidationError):
    """Raised when credentials are invalid."""

    def __init__(self, message: str = "Invalid credentials") -> None:
        super().__init__(message)


class InvalidFileError(ValidationError):
    """Raised when a file is invalid (wrong type, size, etc.)."""

    def __init__(self, message: str = "Invalid file") -> None:
        super().__init__(message)


class InvalidConfigurationError(ValidationError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str = "Invalid configuration") -> None:
        super().__init__(message)


class PasswordValidationError(ValidationError):
    """Raised when password doesn't meet requirements."""

    def __init__(self, message: str = "Password does not meet requirements") -> None:
        super().__init__(message)


class InvalidLicenseDataError(ValidationError):
    """Raised when license data is invalid."""

    def __init__(self, message: str = "Invalid license data") -> None:
        super().__init__(message)


# =============================================================================
# Permission Errors (403)
# =============================================================================


class PermissionError(LicenceAPIError):
    """Base class for permission errors."""

    pass


class InsufficientPermissionsError(PermissionError):
    """Raised when user lacks required permissions."""

    def __init__(self, permission: str | None = None) -> None:
        message = "Insufficient permissions"
        details = {"required_permission": permission} if permission else {}
        super().__init__(message, details)


class CannotDeleteSelfError(PermissionError):
    """Raised when user tries to delete themselves."""

    def __init__(self) -> None:
        super().__init__("Cannot delete your own account")


class CannotModifySystemRoleError(PermissionError):
    """Raised when trying to modify a system role."""

    def __init__(self, role_code: str | None = None) -> None:
        message = "Cannot modify system role"
        details = {"role_code": role_code} if role_code else {}
        super().__init__(message, details)


# =============================================================================
# Operation Errors (500)
# =============================================================================


class OperationError(LicenceAPIError):
    """Base class for operation errors."""

    pass


class SyncError(OperationError):
    """Raised when a sync operation fails."""

    def __init__(self, message: str = "Sync operation failed") -> None:
        super().__init__(message)


class BackupError(OperationError):
    """Raised when a backup operation fails."""

    def __init__(self, message: str = "Backup operation failed") -> None:
        super().__init__(message)


class RestoreError(OperationError):
    """Raised when a restore operation fails."""

    def __init__(self, message: str = "Restore operation failed") -> None:
        super().__init__(message)


class EncryptionError(OperationError):
    """Raised when encryption/decryption fails."""

    def __init__(self, message: str = "Encryption operation failed") -> None:
        super().__init__(message)


# =============================================================================
# Authentication Errors (401)
# =============================================================================


class AuthenticationError(LicenceAPIError):
    """Base class for authentication errors."""

    pass


class SessionExpiredError(AuthenticationError):
    """Raised when session has expired."""

    def __init__(self) -> None:
        super().__init__("Session expired")


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid token")


class AccountLockedError(AuthenticationError):
    """Raised when account is locked."""

    def __init__(self) -> None:
        super().__init__("Account is locked")
