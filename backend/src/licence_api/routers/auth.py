"""Authentication router."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.config import get_settings
from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.auth import (
    LocalLoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserInfo,
)
from licence_api.security.auth import get_current_user
from licence_api.security.csrf import generate_csrf_token, validate_csrf
from licence_api.security.rate_limit import (
    AUTH_LOGIN_LIMIT,
    AUTH_LOGOUT_LIMIT,
    AUTH_PASSWORD_CHANGE_LIMIT,
    AUTH_REFRESH_LIMIT,
    limiter,
)
from licence_api.services.auth_service import AuthService

router = APIRouter()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str | None) -> None:
    """Set authentication cookies on response.

    Uses cookie security settings from configuration.

    Args:
        response: FastAPI response
        access_token: JWT access token
        refresh_token: Refresh token (optional)
    """
    settings = get_settings()

    # Determine secure flag from config (override in development)
    is_secure = settings.session_cookie_secure
    if settings.environment == "development":
        is_secure = False

    # Set access token cookie (short-lived)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.session_cookie_httponly,
        secure=is_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.jwt_expiration_hours * 3600,
        path="/",
    )

    # Set refresh token cookie (long-lived)
    # Path set to / to ensure cookie is sent with all requests for token refresh
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=settings.session_cookie_httponly,
            secure=is_secure,
            samesite=settings.session_cookie_samesite,
            max_age=settings.refresh_token_days * 24 * 3600,
            path="/",
        )


def _clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies.

    Args:
        response: FastAPI response
    """
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


class LogoutRequest(BaseModel):
    """Logout request."""

    refresh_token: str | None = None


class CsrfTokenResponse(BaseModel):
    """CSRF token response."""

    csrf_token: str


@router.get("/csrf-token", response_model=CsrfTokenResponse)
async def get_csrf_token(response: Response) -> CsrfTokenResponse:
    """Get a CSRF token for state-changing requests.

    The token is returned in the response body and also set as a cookie.
    Include the token in the X-CSRF-Token header for POST/PUT/DELETE requests.
    """
    settings = get_settings()
    token, signed_token = generate_csrf_token()

    # Determine secure flag from config (override in development)
    is_secure = settings.session_cookie_secure
    if settings.environment == "development":
        is_secure = False

    # Set CSRF cookie (readable by JavaScript for double-submit pattern)
    response.set_cookie(
        key="csrf_token",
        value=signed_token,
        httponly=False,  # Must be readable by JavaScript for CSRF protection
        secure=is_secure,
        samesite=settings.session_cookie_samesite,
        max_age=8 * 3600,  # 8 hours
        path="/",
    )

    return CsrfTokenResponse(csrf_token=signed_token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(AUTH_LOGIN_LIMIT)
async def login_local(
    request: Request,
    response: Response,
    body: LocalLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_agent: str | None = Header(default=None),
) -> TokenResponse:
    """Authenticate with email and password.

    Returns JWT access token and refresh token.
    Tokens are also set as httpOnly cookies for enhanced security.
    """
    service = AuthService(db)
    ip_address = request.client.host if request.client else None

    token_response = await service.authenticate_local(
        email=body.email,
        password=body.password,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Set httpOnly cookies for XSS protection
    _set_auth_cookies(response, token_response.access_token, token_response.refresh_token)

    return token_response


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def refresh_token(
    request: Request,
    response: Response,
    body: RefreshTokenRequest | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
) -> TokenResponse:
    """Refresh access token using refresh token.

    Accepts refresh token from request body or httpOnly cookie.
    """
    # Prefer cookie over body for security
    token = refresh_token_cookie
    if not token and body:
        token = body.refresh_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    service = AuthService(db)
    token_response = await service.refresh_access_token(token)

    # Update access token cookie
    _set_auth_cookies(response, token_response.access_token, None)

    return token_response


@router.post("/logout")
@limiter.limit(AUTH_LOGOUT_LIMIT)
async def logout(
    request: Request,
    response: Response,
    body: LogoutRequest | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    user_agent: str | None = Header(default=None),
) -> dict[str, str]:
    """Logout and revoke refresh token.

    Accepts refresh token from request body or httpOnly cookie.
    """
    # Prefer cookie over body
    token = refresh_token_cookie
    if not token and body:
        token = body.refresh_token

    if token:
        ip_address = request.client.host if request.client else None
        service = AuthService(db)
        await service.logout(token, ip_address=ip_address, user_agent=user_agent)

    # Clear auth cookies
    _clear_auth_cookies(response)

    return {"message": "Logout successful"}


@router.post("/logout-all")
async def logout_all_sessions(
    response: Response,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    """Logout all sessions for the current user."""
    service = AuthService(db)
    count = await service.logout_all_sessions(current_user.id)

    # Clear auth cookies
    _clear_auth_cookies(response)

    return {"sessions_revoked": count}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserInfo:
    """Get current user information including roles and permissions."""
    service = AuthService(db)
    user_info = await service.get_user_info(current_user.id)

    if user_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user_info


@router.post("/change-password")
@limiter.limit(AUTH_PASSWORD_CHANGE_LIMIT)
async def change_password(
    request: Request,
    body: PasswordChangeRequest,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_agent: str | None = Header(default=None),
) -> dict[str, str]:
    """Change current user's password."""
    ip_address = request.client.host if request.client else None
    service = AuthService(db)
    await service.change_password(
        user_id=current_user.id,
        current_password=body.current_password,
        new_password=body.new_password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {"message": "Password changed successfully"}
