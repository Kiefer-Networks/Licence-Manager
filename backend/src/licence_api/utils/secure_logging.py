"""Secure logging utilities to prevent information disclosure."""

import logging
import re
from functools import lru_cache
from typing import Any

from licence_api.config import get_settings


@lru_cache(maxsize=1)
def is_debug_mode() -> bool:
    """Check if application is running in debug mode."""
    settings = get_settings()
    return settings.debug


def sanitize_exception_message(error: Exception) -> str:
    """Sanitize exception message for logging in production.

    Removes potentially sensitive information like:
    - File system paths
    - Database connection strings
    - Email addresses
    - API keys/tokens

    Args:
        error: The exception to sanitize

    Returns:
        Sanitized error message suitable for production logs
    """
    error_msg = str(error)

    # Remove file paths (Unix and Windows)
    error_msg = re.sub(r"['\"]?(/[a-zA-Z0-9_./\-]+|[A-Z]:\\[^\s'\"]+)['\"]?", "[PATH]", error_msg)

    # Remove anything that looks like a connection string
    url_pattern = r"(postgresql|mysql|sqlite|mongodb|redis|http|https)://[^\s]+"
    error_msg = re.sub(url_pattern, "[URL]", error_msg)

    # Remove email addresses
    error_msg = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL]", error_msg)

    # Remove potential API keys/tokens (long alphanumeric strings)
    error_msg = re.sub(r"[a-zA-Z0-9_\-]{32,}", "[TOKEN]", error_msg)

    # Truncate very long messages
    if len(error_msg) > 200:
        error_msg = error_msg[:197] + "..."

    return error_msg


def log_error(
    logger: logging.Logger,
    message: str,
    error: Exception | None = None,
    **kwargs: Any,
) -> None:
    """Log an error with appropriate detail level based on environment.

    In debug mode, logs full exception details.
    In production, logs sanitized message without sensitive details.

    Args:
        logger: The logger instance to use
        message: The log message (should be generic, no sensitive data)
        error: Optional exception to include
        **kwargs: Additional context to log (will be sanitized in production)
    """
    if is_debug_mode():
        # In debug mode, log full details
        if error:
            logger.error(f"{message}: {error}", exc_info=True, extra=kwargs)
        else:
            logger.error(message, extra=kwargs)
    else:
        # In production, log sanitized message
        if error:
            sanitized = sanitize_exception_message(error)
            logger.error(f"{message}: {sanitized}")
        else:
            logger.error(message)


def log_warning(
    logger: logging.Logger,
    message: str,
    error: Exception | None = None,
    **kwargs: Any,
) -> None:
    """Log a warning with appropriate detail level based on environment.

    In debug mode, logs full exception details.
    In production, logs sanitized message without sensitive details.

    Args:
        logger: The logger instance to use
        message: The log message (should be generic, no sensitive data)
        error: Optional exception to include
        **kwargs: Additional context to log (will be sanitized in production)
    """
    if is_debug_mode():
        # In debug mode, log full details
        if error:
            logger.warning(f"{message}: {error}", extra=kwargs)
        else:
            logger.warning(message, extra=kwargs)
    else:
        # In production, log sanitized message
        if error:
            sanitized = sanitize_exception_message(error)
            logger.warning(f"{message}: {sanitized}")
        else:
            logger.warning(message)
