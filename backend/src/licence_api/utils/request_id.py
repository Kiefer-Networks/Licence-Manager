"""Request ID generation utilities."""

import uuid


def generate_request_id() -> str:
    """Generate a unique request ID for tracing.

    Returns:
        A UUID4 string for request tracking across the application.
    """
    return str(uuid.uuid4())
