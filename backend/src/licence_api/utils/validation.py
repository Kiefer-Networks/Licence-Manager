"""Input validation utilities to prevent injection attacks."""

import re
from typing import TypeVar

# Maximum lengths for common fields
MAX_SEARCH_LENGTH = 200
MAX_DEPARTMENT_LENGTH = 100
MAX_STATUS_LENGTH = 50
MAX_SORT_BY_LENGTH = 50

# Pattern for safe text input (letters, numbers, spaces, common punctuation)
SAFE_TEXT_PATTERN = re.compile(r'^[\w\s\-.,&()\'"/]+$', re.UNICODE)

# Pattern for safe sort direction
SORT_DIR_PATTERN = re.compile(r'^(asc|desc)$', re.IGNORECASE)


def sanitize_search(search: str | None, max_length: int = MAX_SEARCH_LENGTH) -> str | None:
    """Sanitize search input.

    Args:
        search: Raw search string
        max_length: Maximum allowed length

    Returns:
        Sanitized search string or None
    """
    if search is None:
        return None

    # Truncate to max length
    search = search[:max_length]

    # Remove any SQL-like patterns that could be used for injection
    # (SQLAlchemy parameterizes these anyway, but defense in depth)
    search = search.replace(';', '').replace('--', '')

    # Strip leading/trailing whitespace
    return search.strip() or None


def sanitize_department(department: str | None, max_length: int = MAX_DEPARTMENT_LENGTH) -> str | None:
    """Sanitize department filter input.

    Args:
        department: Raw department string
        max_length: Maximum allowed length

    Returns:
        Sanitized department string or None
    """
    if department is None:
        return None

    # Truncate to max length
    department = department[:max_length]

    # Strip whitespace
    department = department.strip()

    if not department:
        return None

    # Validate against safe pattern
    if not SAFE_TEXT_PATTERN.match(department):
        return None

    return department


def validate_sort_direction(sort_dir: str) -> str:
    """Validate and normalize sort direction.

    Args:
        sort_dir: Raw sort direction

    Returns:
        Normalized sort direction ('asc' or 'desc')
    """
    if sort_dir and SORT_DIR_PATTERN.match(sort_dir):
        return sort_dir.lower()
    return "desc"  # Default to descending


def validate_sort_by(sort_by: str, allowed_columns: set[str], default: str) -> str:
    """Validate sort column against whitelist.

    Args:
        sort_by: Raw sort column name
        allowed_columns: Set of allowed column names
        default: Default column if invalid

    Returns:
        Validated sort column name
    """
    if sort_by and sort_by in allowed_columns:
        return sort_by
    return default


def sanitize_status(status: str | None, allowed_values: set[str] | None = None) -> str | None:
    """Sanitize status filter input.

    Args:
        status: Raw status string
        allowed_values: Optional set of allowed status values

    Returns:
        Sanitized status string or None
    """
    if status is None:
        return None

    # Truncate and strip
    status = status[:MAX_STATUS_LENGTH].strip().lower()

    if not status:
        return None

    # If allowed values specified, validate against them
    if allowed_values and status not in allowed_values:
        return None

    return status
