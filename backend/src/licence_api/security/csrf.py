"""CSRF protection utilities."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from licence_api.config import get_settings

# CSRF token validity duration
CSRF_TOKEN_LIFETIME = timedelta(hours=8)


def generate_csrf_token() -> tuple[str, str]:
    """Generate a CSRF token and its signature.

    Returns:
        Tuple of (token, signature)
    """
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    timestamp = int(datetime.now(timezone.utc).timestamp())
    message = f"{token}:{timestamp}"
    signature = hmac.new(
        settings.jwt_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return token, f"{token}:{timestamp}:{signature}"


def verify_csrf_token(signed_token: str) -> bool:
    """Verify a CSRF token signature and expiry.

    Args:
        signed_token: The signed CSRF token (token:timestamp:signature)

    Returns:
        True if valid, False otherwise
    """
    try:
        parts = signed_token.split(":")
        if len(parts) != 3:
            return False

        token, timestamp_str, provided_signature = parts
        timestamp = int(timestamp_str)

        # Check expiry
        created_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        if datetime.now(timezone.utc) - created_at > CSRF_TOKEN_LIFETIME:
            return False

        # Verify signature
        settings = get_settings()
        message = f"{token}:{timestamp}"
        expected_signature = hmac.new(
            settings.jwt_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(provided_signature, expected_signature)
    except (ValueError, TypeError):
        return False


async def validate_csrf(
    request: Request,
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias="csrf_token")] = None,
) -> None:
    """Validate CSRF token for state-changing requests.

    This dependency should be added to POST, PUT, DELETE endpoints.

    Args:
        request: The FastAPI request
        x_csrf_token: CSRF token from header
        csrf_cookie: CSRF token from cookie

    Raises:
        HTTPException: If CSRF validation fails
    """
    # Skip CSRF for safe methods
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Require CSRF token
    if not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing",
        )

    # Verify token signature and expiry
    if not verify_csrf_token(x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired CSRF token",
        )

    # Verify cookie matches header token (double submit cookie pattern)
    if csrf_cookie:
        # Extract token part from signed token
        header_token = x_csrf_token.split(":")[0] if ":" in x_csrf_token else x_csrf_token
        cookie_token = csrf_cookie.split(":")[0] if ":" in csrf_cookie else csrf_cookie
        if not hmac.compare_digest(header_token, cookie_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token mismatch",
            )
