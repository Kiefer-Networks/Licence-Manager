"""Authentication and authorization utilities."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from licence_api.config import get_settings
from licence_api.models.domain.admin_user import AdminUser

security = HTTPBearer(auto_error=False)


def create_access_token(
    user_id: UUID,
    email: str,
    roles: list[str],
    permissions: list[str],
) -> str:
    """Create a JWT access token.

    Args:
        user_id: User UUID
        email: User email
        roles: List of role codes
        permissions: List of permission codes

    Returns:
        JWT token string
    """
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expiration_hours)

    payload = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "permissions": permissions,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token() -> tuple[str, str]:
    """Create a refresh token.

    Returns:
        Tuple of (raw_token, token_hash)
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token.

    Args:
        token: Raw refresh token

    Returns:
        Hashed token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Validates signature, expiration, issuer (iss), and audience (aud) claims.

    Args:
        token: JWT token string

    Returns:
        Token payload

    Raises:
        HTTPException: If token is invalid, expired, or has invalid claims
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "require_iat": True,
                "require_exp": True,
                "require_sub": True,
            },
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(HTTPBearer(auto_error=False)),
    ] = None,
) -> AdminUser:
    """Get the current authenticated user from JWT token.

    Accepts token from Authorization header or httpOnly cookie.

    Args:
        request: FastAPI request (for cookie access)
        credentials: HTTP Bearer credentials

    Returns:
        AdminUser domain model

    Raises:
        HTTPException: If authentication fails
    """
    token: str | None = None

    # Try Authorization header first
    if credentials is not None:
        token = credentials.credentials
    else:
        # Fall back to httpOnly cookie
        token = request.cookies.get("access_token")

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    return AdminUser(
        id=UUID(payload["sub"]),
        email=payload["email"],
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", []),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def require_permission(*required_permissions: str):
    """Dependency factory to require specific permissions.

    Args:
        required_permissions: Permission codes required (any one)

    Returns:
        Dependency function
    """

    async def permission_dependency(
        current_user: Annotated[AdminUser, Depends(get_current_user)],
    ) -> AdminUser:
        if not current_user.has_any_permission(*required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return permission_dependency


async def require_superadmin(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
) -> AdminUser:
    """Require the current user to be a superadmin.

    Args:
        current_user: Current authenticated user

    Returns:
        AdminUser if they are superadmin

    Raises:
        HTTPException: If user is not superadmin
    """
    if not current_user.is_superadmin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return current_user


async def require_admin(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
) -> AdminUser:
    """Require the current user to be an admin or higher.

    Args:
        current_user: Current authenticated user

    Returns:
        AdminUser if they are admin or higher

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# Permission constants for easy access
class Permissions:
    """Permission code constants."""

    # Dashboard
    DASHBOARD_VIEW = "dashboard.view"

    # Users
    USERS_VIEW = "users.view"
    USERS_CREATE = "users.create"
    USERS_EDIT = "users.edit"
    USERS_DELETE = "users.delete"
    USERS_MANAGE_ROLES = "users.manage_roles"

    # Roles
    ROLES_VIEW = "roles.view"
    ROLES_CREATE = "roles.create"
    ROLES_EDIT = "roles.edit"
    ROLES_DELETE = "roles.delete"

    # Providers
    PROVIDERS_VIEW = "providers.view"
    PROVIDERS_CREATE = "providers.create"
    PROVIDERS_EDIT = "providers.edit"
    PROVIDERS_DELETE = "providers.delete"
    PROVIDERS_SYNC = "providers.sync"

    # Licenses
    LICENSES_VIEW = "licenses.view"
    LICENSES_CREATE = "licenses.create"
    LICENSES_EDIT = "licenses.edit"
    LICENSES_DELETE = "licenses.delete"
    LICENSES_ASSIGN = "licenses.assign"
    LICENSES_BULK_ACTIONS = "licenses.bulk_actions"
    LICENSES_IMPORT = "licenses.import"

    # Employees
    EMPLOYEES_VIEW = "employees.view"
    EMPLOYEES_CREATE = "employees.create"
    EMPLOYEES_EDIT = "employees.edit"
    EMPLOYEES_DELETE = "employees.delete"

    # Reports
    REPORTS_VIEW = "reports.view"
    REPORTS_EXPORT = "reports.export"

    # Settings
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"
    SETTINGS_DELETE = "settings.delete"

    # Payment Methods
    PAYMENT_METHODS_VIEW = "payment_methods.view"
    PAYMENT_METHODS_CREATE = "payment_methods.create"
    PAYMENT_METHODS_EDIT = "payment_methods.edit"
    PAYMENT_METHODS_DELETE = "payment_methods.delete"

    # Audit
    AUDIT_VIEW = "audit.view"
    AUDIT_EXPORT = "audit.export"

    # System
    SYSTEM_ADMIN = "system.admin"
