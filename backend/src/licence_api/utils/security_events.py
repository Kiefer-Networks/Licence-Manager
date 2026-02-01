"""Security event logging for sensitive operations.

This module provides a dedicated security logger for tracking security-relevant
events such as authentication attempts, password changes, and role modifications.
These events are logged separately from application logs for security monitoring
and compliance purposes.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID


class SecurityEventType(str, Enum):
    """Types of security events that are logged."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_LOCKED = "login_locked"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"

    # Account management
    USER_CREATED = "user_created"
    USER_DISABLED = "user_disabled"
    USER_ENABLED = "user_enabled"
    USER_DELETED = "user_deleted"

    # Password events
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"

    # Role and permission events
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    ROLE_CREATED = "role_created"
    ROLE_DELETED = "role_deleted"
    PERMISSION_CHANGED = "permission_changed"

    # Session events
    SESSION_CREATED = "session_created"
    SESSION_REVOKED = "session_revoked"
    ALL_SESSIONS_REVOKED = "all_sessions_revoked"


# Create a dedicated security logger with its own handler
security_logger = logging.getLogger("security")


def log_security_event(
    event_type: SecurityEventType,
    user_id: UUID | str | None = None,
    user_email: str | None = None,
    target_user_id: UUID | str | None = None,
    target_user_email: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: dict[str, Any] | None = None,
    success: bool = True,
) -> None:
    """Log a security event.

    Args:
        event_type: The type of security event
        user_id: The ID of the user performing the action
        user_email: The email of the user performing the action
        target_user_id: The ID of the user being affected (for admin actions)
        target_user_email: The email of the user being affected
        ip_address: The client IP address
        user_agent: The client user agent
        details: Additional event-specific details
        success: Whether the operation succeeded
    """
    event_data = {
        "event_type": event_type.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "actor": {
            "user_id": str(user_id) if user_id else None,
            "email": user_email,
            "ip_address": ip_address,
            "user_agent": user_agent,
        },
    }

    # Add target user for admin actions
    if target_user_id or target_user_email:
        event_data["target"] = {
            "user_id": str(target_user_id) if target_user_id else None,
            "email": target_user_email,
        }

    # Add any additional details
    if details:
        event_data["details"] = details

    # Log at appropriate level based on success
    if success:
        security_logger.info(
            f"Security event: {event_type.value}",
            extra={"security_event": event_data},
        )
    else:
        security_logger.warning(
            f"Security event (failed): {event_type.value}",
            extra={"security_event": event_data},
        )
