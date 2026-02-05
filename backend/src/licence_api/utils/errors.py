"""Centralized HTTP error helpers for routers.

These functions provide consistent error responses across all routers.
"""

from typing import NoReturn

from fastapi import HTTPException, status


def raise_not_found(entity: str = "Resource") -> NoReturn:
    """Raise a 404 Not Found error.

    Args:
        entity: The name of the entity that was not found (e.g., "License", "User")

    Raises:
        HTTPException: With 404 status code
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} not found",
    )


def raise_conflict(message: str = "Resource already exists") -> NoReturn:
    """Raise a 409 Conflict error.

    Args:
        message: The error message to return

    Raises:
        HTTPException: With 409 status code
    """
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=message,
    )


def raise_bad_request(message: str = "Invalid request") -> NoReturn:
    """Raise a 400 Bad Request error.

    Args:
        message: The error message to return

    Raises:
        HTTPException: With 400 status code
    """
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
    )


def raise_forbidden(message: str = "Access denied") -> NoReturn:
    """Raise a 403 Forbidden error.

    Args:
        message: The error message to return

    Raises:
        HTTPException: With 403 status code
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message,
    )


def raise_unauthorized(message: str = "Authentication required") -> NoReturn:
    """Raise a 401 Unauthorized error.

    Args:
        message: The error message to return

    Raises:
        HTTPException: With 401 status code
    """
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
    )
