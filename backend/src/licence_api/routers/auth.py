"""Authentication router."""

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.config import get_settings
from licence_api.constants.paths import ADMIN_AVATAR_DIR
from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.auth import (
    AvatarUploadResponse,
    LoginResponse,
    NotificationEventType,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RefreshTokenRequest,
    TokenResponse,
    TotpBackupCodesResponse,
    TotpDisableRequest,
    TotpEnableResponse,
    TotpLoginRequest,
    TotpSetupResponse,
    TotpStatusResponse,
    TotpVerifyRequest,
    UserInfo,
    UserNotificationPreferenceBulkUpdate,
    UserNotificationPreferenceResponse,
    UserNotificationPreferencesResponse,
    UserNotificationPreferenceUpdate,
)
from licence_api.security.auth import get_current_user
from licence_api.security.csrf import CSRFProtected, generate_csrf_token
from licence_api.security.rate_limit import (
    AUTH_LOGIN_LIMIT,
    AUTH_LOGOUT_LIMIT,
    AUTH_PASSWORD_CHANGE_LIMIT,
    AUTH_REFRESH_LIMIT,
    limiter,
)
from licence_api.services.auth_service import AuthService

router = APIRouter()

# CSRF token TTL in seconds (8 hours)
CSRF_TOKEN_TTL_SECONDS = 8 * 3600


# Dependency injection
def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get AuthService instance."""
    return AuthService(db)


# Available notification event types
NOTIFICATION_EVENT_TYPES = [
    NotificationEventType(
        code="license_expiring",
        name="License Expiring",
        description="Contract or license about to expire",
        category="licenses",
    ),
    NotificationEventType(
        code="license_inactive",
        name="Inactive License",
        description="License not used for extended period",
        category="licenses",
    ),
    NotificationEventType(
        code="license_unassigned",
        name="Unassigned License",
        description="License not assigned to any employee",
        category="licenses",
    ),
    NotificationEventType(
        code="employee_offboarded",
        name="Employee Offboarded",
        description="Employee has been offboarded with active licenses",
        category="employees",
    ),
    NotificationEventType(
        code="utilization_low",
        name="Low Utilization",
        description="Provider utilization below threshold",
        category="utilization",
    ),
    NotificationEventType(
        code="cost_increase",
        name="Cost Increase",
        description="Monthly costs increased significantly",
        category="costs",
    ),
    NotificationEventType(
        code="duplicate_detected",
        name="Duplicate Detected",
        description="Potential duplicate account detected",
        category="duplicates",
    ),
    NotificationEventType(
        code="sync_failed",
        name="Sync Failed",
        description="Provider sync failed",
        category="system",
    ),
    NotificationEventType(
        code="sync_completed",
        name="Sync Completed",
        description="Provider sync completed successfully",
        category="system",
    ),
]

EVENT_TYPE_MAP = {e.code: e for e in NOTIFICATION_EVENT_TYPES}


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str | None = None
) -> None:
    """Set authentication cookies on response.

    Uses cookie security settings from configuration.

    Args:
        response: FastAPI response to set cookies on
        access_token: JWT access token to store
        refresh_token: Refresh token to store (optional)

    Returns:
        None
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
        response: FastAPI response to clear cookies from

    Returns:
        None
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
@limiter.limit(AUTH_REFRESH_LIMIT)
async def get_csrf_token(request: Request, response: Response) -> CsrfTokenResponse:
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
        max_age=CSRF_TOKEN_TTL_SECONDS,
        path="/",
    )

    return CsrfTokenResponse(csrf_token=signed_token)


@router.post("/login", response_model=LoginResponse)
@limiter.limit(AUTH_LOGIN_LIMIT)
async def login_local(
    request: Request,
    response: Response,
    body: TotpLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_agent: str | None = Header(default=None),
) -> LoginResponse:
    """Authenticate with email, password, and optional TOTP code.

    If 2FA is enabled and no TOTP code is provided, returns totp_required=true.
    If authentication succeeds, returns JWT tokens.
    Tokens are also set as httpOnly cookies for enhanced security.
    """
    ip_address = request.client.host if request.client else None

    login_response = await auth_service.authenticate_local(
        email=body.email,
        password=body.password,
        totp_code=body.totp_code,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Set httpOnly cookies for XSS protection (only if tokens were issued)
    if login_response.access_token:
        _set_auth_cookies(response, login_response.access_token, login_response.refresh_token)

    return login_response


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def refresh_token(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    body: RefreshTokenRequest | None = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    user_agent: str | None = Header(default=None),
) -> TokenResponse:
    """Refresh access token using refresh token.

    Implements refresh token rotation for enhanced security.
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

    ip_address = request.client.host if request.client else None
    token_response = await auth_service.refresh_access_token(
        token,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Update both access and refresh token cookies (rotation)
    _set_auth_cookies(response, token_response.access_token, token_response.refresh_token)

    return token_response


@router.post("/logout")
@limiter.limit(AUTH_LOGOUT_LIMIT)
async def logout(
    request: Request,
    response: Response,
    body: LogoutRequest | None = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    user_agent: str | None = Header(default=None),
    _csrf: Annotated[None, Depends(CSRFProtected())] = None,
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
        await auth_service.logout(token, ip_address=ip_address, user_agent=user_agent)

    # Clear auth cookies
    _clear_auth_cookies(response)

    return {"message": "Logout successful"}


@router.post("/logout-all")
@limiter.limit(AUTH_REFRESH_LIMIT)
async def logout_all_sessions(
    request: Request,
    response: Response,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> dict[str, int]:
    """Logout all sessions for the current user."""
    count = await auth_service.logout_all_sessions(current_user.id)

    # Clear auth cookies
    _clear_auth_cookies(response)

    return {"sessions_revoked": count}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserInfo:
    """Get current user information including roles and permissions."""
    user_info = await auth_service.get_user_info(current_user.id)

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
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    user_agent: str | None = Header(default=None),
) -> dict[str, str]:
    """Change current user's password."""
    ip_address = request.client.host if request.client else None
    await auth_service.change_password(
        user_id=current_user.id,
        current_password=body.current_password,
        new_password=body.new_password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {"message": "Password changed successfully"}


# TOTP Two-Factor Authentication Endpoints

# Rate limit for TOTP operations (stricter due to security sensitivity)
AUTH_TOTP_LIMIT = "10/minute"


@router.get("/totp/status", response_model=TotpStatusResponse)
async def get_totp_status(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TotpStatusResponse:
    """Get current TOTP status including backup codes remaining."""
    return await auth_service.get_totp_status(current_user.id)


@router.post("/totp/setup", response_model=TotpSetupResponse)
@limiter.limit(AUTH_TOTP_LIMIT)
async def setup_totp(
    request: Request,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> TotpSetupResponse:
    """Initialize TOTP setup and get QR code.

    Returns a QR code and secret for the authenticator app.
    TOTP is not enabled until verified with /totp/verify.
    """
    return await auth_service.setup_totp(current_user.id)


@router.post("/totp/verify", response_model=TotpEnableResponse)
@limiter.limit(AUTH_TOTP_LIMIT)
async def verify_and_enable_totp(
    request: Request,
    body: TotpVerifyRequest,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    user_agent: str | None = Header(default=None),
) -> TotpEnableResponse:
    """Verify TOTP code and enable two-factor authentication.

    Must be called after /totp/setup with a valid code from the authenticator app.
    Returns backup codes that should be stored securely.
    """
    ip_address = request.client.host if request.client else None
    return await auth_service.verify_and_enable_totp(
        user_id=current_user.id,
        code=body.code,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post("/totp/disable")
@limiter.limit(AUTH_TOTP_LIMIT)
async def disable_totp(
    request: Request,
    body: TotpDisableRequest,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    user_agent: str | None = Header(default=None),
) -> dict[str, str]:
    """Disable two-factor authentication.

    Requires password verification for security.
    """
    ip_address = request.client.host if request.client else None
    await auth_service.disable_totp(
        user_id=current_user.id,
        password=body.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {"message": "Two-factor authentication disabled successfully"}


@router.post("/totp/backup-codes", response_model=TotpBackupCodesResponse)
@limiter.limit(AUTH_TOTP_LIMIT)
async def regenerate_backup_codes(
    request: Request,
    body: TotpDisableRequest,  # Re-use password request
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    user_agent: str | None = Header(default=None),
) -> TotpBackupCodesResponse:
    """Regenerate backup codes.

    Requires password verification for security.
    Previous backup codes will be invalidated.
    """
    ip_address = request.client.host if request.client else None
    return await auth_service.regenerate_backup_codes(
        user_id=current_user.id,
        password=body.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )


# Profile Update Endpoints


@router.patch("/me", response_model=UserInfo)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def update_profile(
    request: Request,
    body: ProfileUpdateRequest,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> UserInfo:
    """Update current user's profile (name and locale preferences)."""
    return await auth_service.update_profile(
        user_id=current_user.id,
        name=body.name,
        language=body.language,
        date_format=body.date_format,
        number_format=body.number_format,
        currency=body.currency,
    )


@router.post("/me/avatar", response_model=AvatarUploadResponse)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def upload_avatar(
    request: Request,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    file: UploadFile = File(...),
) -> AvatarUploadResponse:
    """Upload avatar image for current user.

    Note: CSRF protection is explicitly applied via CSRFProtected dependency.
    """
    content = await file.read()

    try:
        picture_url = await auth_service.upload_avatar(
            user_id=current_user.id,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
        return AvatarUploadResponse(picture_url=picture_url)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid avatar file",
        )


@router.get("/avatar/{user_id}")
async def get_avatar(
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
) -> Response:
    """Get avatar image for a user. Requires authentication."""
    # FastAPI validates UUID format automatically via type annotation
    # Try to find avatar with any extension
    for ext in [".jpg", ".png", ".gif", ".webp"]:
        file_path = ADMIN_AVATAR_DIR / f"{user_id}{ext}"
        if file_path.exists():
            content_type = "image/jpeg"
            if ext == ".png":
                content_type = "image/png"
            elif ext == ".gif":
                content_type = "image/gif"
            elif ext == ".webp":
                content_type = "image/webp"

            content = file_path.read_bytes()
            return Response(
                content=content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=3600"},
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Avatar not found",
    )


@router.delete("/me/avatar")
@limiter.limit(AUTH_REFRESH_LIMIT)
async def delete_avatar(
    request: Request,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> dict[str, str]:
    """Delete current user's avatar."""
    await auth_service.delete_avatar(current_user.id)
    return {"message": "Avatar deleted successfully"}


# Notification Preferences Endpoints


@router.get("/me/notification-preferences", response_model=UserNotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserNotificationPreferencesResponse:
    """Get current user's notification preferences."""
    prefs = await auth_service.get_notification_preferences(current_user.id)

    # Build response with event type info
    pref_responses = []
    for pref in prefs:
        event_info = EVENT_TYPE_MAP.get(pref.event_type)
        pref_responses.append(
            UserNotificationPreferenceResponse(
                id=pref.id,
                event_type=pref.event_type,
                event_name=event_info.name if event_info else pref.event_type,
                event_description=event_info.description if event_info else "",
                enabled=pref.enabled,
                slack_dm=pref.slack_dm,
                slack_channel=pref.slack_channel,
            )
        )

    return UserNotificationPreferencesResponse(
        preferences=pref_responses,
        available_event_types=NOTIFICATION_EVENT_TYPES,
    )


@router.put("/me/notification-preferences", response_model=UserNotificationPreferencesResponse)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def update_notification_preferences(
    request: Request,
    body: UserNotificationPreferenceBulkUpdate,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> UserNotificationPreferencesResponse:
    """Update current user's notification preferences (bulk)."""
    # Convert to list of dicts for bulk upsert
    prefs_data = [
        {
            "event_type": p.event_type,
            "enabled": p.enabled,
            "slack_dm": p.slack_dm,
            "slack_channel": p.slack_channel,
        }
        for p in body.preferences
    ]

    prefs = await auth_service.update_notification_preferences_bulk(current_user.id, prefs_data)

    # Build response with event type info
    pref_responses = []
    for pref in prefs:
        event_info = EVENT_TYPE_MAP.get(pref.event_type)
        pref_responses.append(
            UserNotificationPreferenceResponse(
                id=pref.id,
                event_type=pref.event_type,
                event_name=event_info.name if event_info else pref.event_type,
                event_description=event_info.description if event_info else "",
                enabled=pref.enabled,
                slack_dm=pref.slack_dm,
                slack_channel=pref.slack_channel,
            )
        )

    return UserNotificationPreferencesResponse(
        preferences=pref_responses,
        available_event_types=NOTIFICATION_EVENT_TYPES,
    )


@router.patch(
    "/me/notification-preferences/{event_type}", response_model=UserNotificationPreferenceResponse
)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def update_single_notification_preference(
    request: Request,
    event_type: str,
    body: UserNotificationPreferenceUpdate,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> UserNotificationPreferenceResponse:
    """Update a single notification preference."""
    if event_type not in EVENT_TYPE_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown event type: {event_type}",
        )

    pref = await auth_service.update_notification_preference(
        user_id=current_user.id,
        event_type=event_type,
        enabled=body.enabled,
        slack_dm=body.slack_dm,
        slack_channel=body.slack_channel,
    )

    event_info = EVENT_TYPE_MAP[event_type]
    return UserNotificationPreferenceResponse(
        id=pref.id,
        event_type=pref.event_type,
        event_name=event_info.name,
        event_description=event_info.description,
        enabled=pref.enabled,
        slack_dm=pref.slack_dm,
        slack_channel=pref.slack_channel,
    )
