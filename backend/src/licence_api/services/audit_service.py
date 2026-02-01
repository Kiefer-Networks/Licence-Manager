"""Audit service for centralized audit logging."""

import logging
from typing import Any, TYPE_CHECKING
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.repositories.audit_repository import AuditRepository

if TYPE_CHECKING:
    from licence_api.models.domain.admin_user import AdminUser

logger = logging.getLogger(__name__)


class AuditAction:
    """Standard audit action types."""

    # Authentication
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    ROLE_ASSIGN = "role_assign"
    ROLE_REVOKE = "role_revoke"

    # Provider management
    PROVIDER_CREATE = "provider_create"
    PROVIDER_UPDATE = "provider_update"
    PROVIDER_DELETE = "provider_delete"
    PROVIDER_SYNC = "provider_sync"
    PROVIDER_TEST = "provider_test"

    # License management
    LICENSE_ASSIGN = "license_assign"
    LICENSE_UNASSIGN = "license_unassign"
    LICENSE_CREATE = "license_create"
    LICENSE_UPDATE = "license_update"
    LICENSE_DELETE = "license_delete"
    LICENSE_BULK_CREATE = "license_bulk_create"
    LICENSE_PACKAGE_CREATE = "license_package_create"
    LICENSE_PACKAGE_UPDATE = "license_package_update"
    LICENSE_PACKAGE_DELETE = "license_package_delete"

    # Settings
    SETTINGS_UPDATE = "settings_update"
    SETTING_UPDATE = "setting_update"
    SETTING_DELETE = "setting_delete"

    # Payment methods
    PAYMENT_METHOD_CREATE = "payment_method_create"
    PAYMENT_METHOD_UPDATE = "payment_method_update"
    PAYMENT_METHOD_DELETE = "payment_method_delete"

    # Files
    FILE_UPLOAD = "file_upload"
    FILE_DELETE = "file_delete"

    # Employee
    EMPLOYEE_CREATE = "employee_create"
    EMPLOYEE_UPDATE = "employee_update"
    EMPLOYEE_DELETE = "employee_delete"
    EMPLOYEE_BULK_IMPORT = "employee_bulk_import"

    # Service Account Patterns
    SERVICE_ACCOUNT_PATTERN_CREATE = "service_account_pattern_create"
    SERVICE_ACCOUNT_PATTERN_DELETE = "service_account_pattern_delete"
    SERVICE_ACCOUNT_PATTERNS_APPLY = "service_account_patterns_apply"

    # Admin Account Patterns
    ADMIN_ACCOUNT_PATTERN_CREATE = "admin_account_pattern_create"
    ADMIN_ACCOUNT_PATTERN_DELETE = "admin_account_pattern_delete"
    ADMIN_ACCOUNT_PATTERNS_APPLY = "admin_account_patterns_apply"

    # Service Account License Types
    SERVICE_ACCOUNT_LICENSE_TYPE_CREATE = "service_account_license_type_create"
    SERVICE_ACCOUNT_LICENSE_TYPE_DELETE = "service_account_license_type_delete"
    SERVICE_ACCOUNT_LICENSE_TYPES_APPLY = "service_account_license_types_apply"

    # Backup
    EXPORT = "export"
    IMPORT = "import"


class ResourceType:
    """Standard resource types for audit logging."""

    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    PROVIDER = "provider"
    LICENSE = "license"
    EMPLOYEE = "employee"
    SETTINGS = "settings"
    SETTING = "setting"
    NOTIFICATION_RULE = "notification_rule"
    PAYMENT_METHOD = "payment_method"
    FILE = "file"
    SESSION = "session"
    SERVICE_ACCOUNT_PATTERN = "service_account_pattern"
    ADMIN_ACCOUNT_PATTERN = "admin_account_pattern"
    SERVICE_ACCOUNT_LICENSE_TYPE = "service_account_license_type"


class AuditService:
    """Service for audit logging operations.

    Provides a centralized way to log audit events across the application.
    All mutations should be logged through this service.
    """

    # Sensitive fields that should be masked in audit logs
    SENSITIVE_FIELDS = frozenset({
        "password",
        "api_key",
        "api_secret",
        "client_secret",
        "access_token",
        "refresh_token",
        "bot_token",
        "user_token",
        "admin_api_key",
        "auth_token",
        "private_key",
        "secret",
        "credentials",
        "service_account_json",
    })

    def __init__(self, session: AsyncSession) -> None:
        """Initialize audit service.

        Args:
            session: Database session
        """
        self.session = session
        self.audit_repo = AuditRepository(session)

    @classmethod
    def _mask_sensitive_data(cls, data: dict[str, Any] | None) -> dict[str, Any] | None:
        """Mask sensitive fields in audit data to prevent credential leakage.

        Args:
            data: Dictionary that may contain sensitive fields

        Returns:
            Dictionary with sensitive values replaced by "[REDACTED]"
        """
        if data is None:
            return None

        masked = {}
        for key, value in data.items():
            if key.lower() in cls.SENSITIVE_FIELDS:
                masked[key] = "[REDACTED]"
            elif isinstance(value, dict):
                masked[key] = cls._mask_sensitive_data(value)
            elif isinstance(value, list):
                masked[key] = [
                    cls._mask_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked[key] = value
        return masked

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: UUID | str | None = None,
        admin_user_id: UUID | None = None,
        user: "AdminUser | None" = None,
        changes: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        request: Request | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log an audit event.

        Args:
            action: Action performed (use AuditAction constants)
            resource_type: Type of resource (use ResourceType constants)
            resource_id: ID of the affected resource
            admin_user_id: ID of the user performing the action (deprecated, use user)
            user: AdminUser object performing the action
            changes: Dictionary of changes made (deprecated, use details)
            details: Dictionary of details/changes to log
            request: FastAPI request object (for extracting IP/user agent)
            ip_address: Client IP (overrides request extraction)
            user_agent: Client user agent (overrides request extraction)
        """
        # Extract user_id from user object if provided
        if user is not None and admin_user_id is None:
            admin_user_id = user.id

        # Use details as changes if provided (backwards compatibility)
        if details is not None and changes is None:
            changes = details

        # Mask sensitive fields to prevent credential leakage in audit logs
        changes = self._mask_sensitive_data(changes)

        # Convert string resource_id to UUID if needed
        if isinstance(resource_id, str):
            try:
                resource_id = UUID(resource_id)
            except ValueError:
                resource_id = None

        # Extract IP and user agent from request if not provided
        if request:
            if not ip_address:
                ip_address = self._get_client_ip(request)
            if not user_agent:
                user_agent = request.headers.get("user-agent", "")

        try:
            await self.audit_repo.log(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                admin_user_id=admin_user_id,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            logger.debug(
                "Audit logged: action=%s resource=%s/%s user=%s",
                action,
                resource_type,
                resource_id,
                admin_user_id,
            )
        except Exception as e:
            # Never fail the main operation due to audit logging
            logger.error("Failed to write audit log: %s", e)

    async def log_login(
        self,
        user_id: UUID,
        success: bool,
        request: Request,
        email: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        """Log a login attempt.

        Args:
            user_id: User attempting to login
            success: Whether login was successful
            request: FastAPI request object
            email: Email used for login attempt
            failure_reason: Reason for failure if not successful
        """
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        changes = {"email": email} if email else {}
        if failure_reason:
            changes["reason"] = failure_reason

        await self.log(
            action=action,
            resource_type=ResourceType.SESSION,
            resource_id=user_id if success else None,
            admin_user_id=user_id if success else None,
            changes=changes,
            request=request,
        )

    async def log_logout(
        self,
        user_id: UUID,
        request: Request,
        all_sessions: bool = False,
    ) -> None:
        """Log a logout event.

        Args:
            user_id: User logging out
            request: FastAPI request object
            all_sessions: Whether all sessions were logged out
        """
        action = AuditAction.LOGOUT_ALL if all_sessions else AuditAction.LOGOUT
        await self.log(
            action=action,
            resource_type=ResourceType.SESSION,
            resource_id=user_id,
            admin_user_id=user_id,
            request=request,
        )

    async def log_entity_change(
        self,
        action: str,
        resource_type: str,
        resource_id: UUID | str,
        user_id: UUID,
        request: Request,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
    ) -> None:
        """Log an entity change with before/after values.

        Args:
            action: Action performed
            resource_type: Type of resource
            resource_id: ID of resource
            user_id: User making the change
            request: FastAPI request object
            old_values: Previous values
            new_values: New values
        """
        changes = {}
        if old_values:
            changes["before"] = old_values
        if new_values:
            changes["after"] = new_values

        await self.log(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            admin_user_id=user_id,
            changes=changes if changes else None,
            request=request,
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check request state first (set by middleware)
        if hasattr(request.state, "client_ip"):
            return request.state.client_ip

        # Check forwarded headers
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
