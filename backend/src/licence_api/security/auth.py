"""Authentication and authorization utilities."""

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from licence_api.config import get_settings
from licence_api.models.domain.admin_user import AdminUser, UserRole

security = HTTPBearer()


class GoogleTokenInfo:
    """Google OAuth token info."""

    def __init__(self, email: str, name: str | None, picture: str | None) -> None:
        self.email = email
        self.name = name
        self.picture = picture


async def verify_google_token(token: str) -> GoogleTokenInfo:
    """Verify a Google OAuth ID token.

    Args:
        token: Google ID token

    Returns:
        GoogleTokenInfo with user details

    Raises:
        HTTPException: If token is invalid
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    data = response.json()

    # Verify audience matches our client ID
    if data.get("aud") != settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token was not issued for this application",
        )

    # Verify email domain if configured
    email = data.get("email")
    if settings.allowed_email_domain:
        if not email or not email.endswith(f"@{settings.allowed_email_domain}"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Email domain must be {settings.allowed_email_domain}",
            )

    return GoogleTokenInfo(
        email=email,
        name=data.get("name"),
        picture=data.get("picture"),
    )


def create_access_token(user_id: UUID, email: str, role: UserRole) -> str:
    """Create a JWT access token.

    Args:
        user_id: User UUID
        email: User email
        role: User role

    Returns:
        JWT token string
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours)

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role.value,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        Token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))] = None,
) -> AdminUser:
    """Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials (optional in dev mode)

    Returns:
        AdminUser domain model

    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_token(credentials.credentials)

    return AdminUser(
        id=UUID(payload["sub"]),
        email=payload["email"],
        role=UserRole(payload["role"]),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


async def require_admin(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
) -> AdminUser:
    """Require the current user to have admin role.

    Args:
        current_user: Current authenticated user

    Returns:
        AdminUser if they have admin role

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
