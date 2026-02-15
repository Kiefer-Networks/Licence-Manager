"""Input validation utilities to prevent injection attacks."""

import re
from typing import Any

# Maximum lengths for common fields
MAX_SEARCH_LENGTH = 200
MAX_DEPARTMENT_LENGTH = 100
MAX_STATUS_LENGTH = 50
MAX_SORT_BY_LENGTH = 50

# Pattern for safe text input (letters, numbers, spaces, common punctuation)
SAFE_TEXT_PATTERN = re.compile(r'^[\w\s\-.,&()\'"/]+$', re.UNICODE)


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
    search = search.replace(";", "").replace("--", "")

    # Strip leading/trailing whitespace
    return search.strip() or None


def sanitize_department(
    department: str | None, max_length: int = MAX_DEPARTMENT_LENGTH
) -> str | None:
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


def validate_against_whitelist(
    value: str | None,
    allowed_values: set[str],
    max_length: int = 50,
) -> str | None:
    """Validate a string value against a whitelist of allowed values.

    Args:
        value: Raw string value
        allowed_values: Set of allowed values
        max_length: Maximum allowed length

    Returns:
        Validated value or None if invalid
    """
    if value is None:
        return None

    # Truncate and strip
    value = value[:max_length].strip()

    if not value:
        return None

    # Validate against whitelist
    if value not in allowed_values:
        return None

    return value


def escape_like_wildcards(value: str) -> str:
    """Escape SQL LIKE wildcards to prevent injection.

    The % and _ characters have special meaning in SQL LIKE patterns:
    - % matches any sequence of characters
    - _ matches any single character

    This function escapes them with backslash to match literally.

    Args:
        value: Raw string value to escape

    Returns:
        Escaped string safe for use in LIKE patterns

    Example:
        >>> escape_like_wildcards("test%value")
        'test\\%value'
        >>> escape_like_wildcards("test_value")
        'test\\_value'
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def validate_dict_recursive(
    data: Any, max_depth: int = 3, current_depth: int = 0, max_items: int = 20
) -> None:
    """Recursively validate dict/list structures to prevent DoS attacks.

    Ensures that nested data structures do not exceed configurable depth
    and item count limits. Validates that all keys are strings and all
    values are of allowed types.

    Args:
        data: The data structure to validate
        max_depth: Maximum nesting depth allowed
        current_depth: Current recursion depth
        max_items: Maximum number of items per collection

    Raises:
        ValueError: If validation fails
    """
    if current_depth > max_depth:
        raise ValueError(f"Credential nesting too deep (max {max_depth} levels)")

    if isinstance(data, dict):
        if len(data) > max_items:
            raise ValueError(f"Too many credential fields (max {max_items})")
        for key, value in data.items():
            if not isinstance(key, str):
                raise ValueError("Credential keys must be strings")
            if len(key) > 100:
                raise ValueError("Credential key too long (max 100 chars)")
            validate_dict_recursive(value, max_depth, current_depth + 1, max_items)
    elif isinstance(data, list):
        if len(data) > max_items:
            raise ValueError(f"Too many items in credential list (max {max_items})")
        for item in data:
            validate_dict_recursive(item, max_depth, current_depth + 1, max_items)
    elif isinstance(data, str):
        if len(data) > 10000:
            raise ValueError("Credential value too long (max 10000 chars)")
    elif isinstance(data, (int, float, bool, type(None))):
        pass  # Primitive types are allowed
    else:
        raise ValueError(f"Invalid credential value type: {type(data).__name__}")
