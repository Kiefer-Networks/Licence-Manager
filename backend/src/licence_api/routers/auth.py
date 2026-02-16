"""Authentication router - Google OAuth only."""

import base64
import hashlib
import logging
import secrets
import urllib.parse
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from authlib.integrations.starlette_client import OAuth
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Header,
    HTTPException,
    Path,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from licence_api.config import get_settings
from licence_api.dependencies import get_auth_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.auth import (
    AvatarUploadResponse,
    LoginResponse,
    NotificationEventType,
    ProfileUpdateRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserInfo,
    UserNotificationPreferenceBulkUpdate,
    UserNotificationPreferenceResponse,
    UserNotificationPreferencesResponse,
    UserNotificationPreferenceUpdate,
)
from licence_api.security.auth import get_current_user
from licence_api.security.csrf import generate_csrf_token
from licence_api.security.rate_limit import (
    API_DEFAULT_LIMIT,
    AUTH_LOGIN_LIMIT,
    AUTH_LOGOUT_LIMIT,
    AUTH_REFRESH_LIMIT,
    EXPENSIVE_READ_LIMIT,
    limiter,
)
from licence_api.services.auth_service import AuthService


def _get_frontend_url() -> str:
    """Get the frontend URL from settings."""
    settings = get_settings()
    return settings.cors_origins_list[0] if settings.cors_origins_list else "/"


def _auth_redirect(error: str) -> RedirectResponse:
    """Create a redirect to the signin page with a URL-encoded error parameter.

    Compliant with RFC 3986 Section 2.1 for proper percent-encoding.
    """
    frontend_url = _get_frontend_url()
    query = urlencode({"error": error})
    return RedirectResponse(url=urllib.parse.urljoin(frontend_url, f"/auth/signin?{query}"))


# Initialize OAuth client (lazy initialization)
_oauth: OAuth | None = None


def get_oauth() -> OAuth:
    """Get or create OAuth client instance."""
    global _oauth
    if _oauth is None:
        _oauth = OAuth()
        settings = get_settings()
        if settings.google_oauth_enabled:
            _oauth.register(
                name="google",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
    return _oauth


router = APIRouter()

# CSRF token TTL in seconds (8 hours)
CSRF_TOKEN_TTL_SECONDS = 8 * 3600


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
    """Set authentication cookies on response."""
    settings = get_settings()

    is_secure = settings.session_cookie_secure
    if settings.environment == "development":
        is_secure = False

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.session_cookie_httponly,
        secure=is_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.jwt_expiration_hours * 3600,
        path="/",
    )

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
    """Clear authentication cookies."""
    settings = get_settings()
    is_secure = settings.session_cookie_secure
    if settings.environment == "development":
        is_secure = False
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=is_secure,
        samesite=settings.session_cookie_samesite,
        httponly=settings.session_cookie_httponly,
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        secure=is_secure,
        samesite=settings.session_cookie_samesite,
        httponly=settings.session_cookie_httponly,
    )


class LogoutRequest(BaseModel):
    """Logout request."""

    refresh_token: str | None = Field(default=None, max_length=2048)


class CsrfTokenResponse(BaseModel):
    """CSRF token response."""

    csrf_token: str


class AuthConfigResponse(BaseModel):
    """Authentication configuration response."""

    google_oauth_enabled: bool


@router.get("/csrf-token", response_model=CsrfTokenResponse)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def get_csrf_token(request: Request, response: Response) -> CsrfTokenResponse:
    """Get a CSRF token for state-changing requests."""
    settings = get_settings()
    token, signed_token = generate_csrf_token()

    is_secure = settings.session_cookie_secure
    if settings.environment == "development":
        is_secure = False

    response.set_cookie(
        key="csrf_token",
        value=signed_token,
        httponly=False,
        secure=is_secure,
        samesite=settings.session_cookie_samesite,
        max_age=CSRF_TOKEN_TTL_SECONDS,
        path="/",
    )

    return CsrfTokenResponse(csrf_token=signed_token)


@router.get("/config", response_model=AuthConfigResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_auth_config(request: Request) -> AuthConfigResponse:
    """Get authentication configuration."""
    settings = get_settings()
    return AuthConfigResponse(google_oauth_enabled=settings.google_oauth_enabled)


@router.get("/google")
@limiter.limit(AUTH_LOGIN_LIMIT)
async def google_login(request: Request) -> RedirectResponse:
    """Initiate Google OAuth flow."""
    settings = get_settings()

    if not settings.google_oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured",
        )

    oauth = get_oauth()

    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state

    # RFC 7636: PKCE - Generate code_verifier and code_challenge
    code_verifier = secrets.token_urlsafe(64)
    request.session["pkce_code_verifier"] = code_verifier
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )

    redirect_uri = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )


@router.get("/google/callback")
@limiter.limit(AUTH_LOGIN_LIMIT)
async def google_callback(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_agent: str | None = Header(default=None),
) -> RedirectResponse:
    """Handle Google OAuth callback.

    Validates the OAuth state parameter per RFC 6749 Section 10.12
    to prevent CSRF attacks during the authorization flow.
    """
    settings = get_settings()

    if not settings.google_oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured",
        )

    # RFC 6749 Section 10.12: Validate state parameter to prevent CSRF
    stored_state = request.session.pop("oauth_state", None)
    received_state = request.query_params.get("state")

    if not stored_state or not received_state:
        logger.warning("OAuth callback missing state parameter")
        return _auth_redirect("oauth_state_missing")

    if not secrets.compare_digest(stored_state, received_state):
        logger.warning("OAuth callback state mismatch (possible CSRF)")
        return _auth_redirect("oauth_state_mismatch")

    # RFC 7636: Retrieve PKCE code_verifier from session
    code_verifier = request.session.pop("pkce_code_verifier", None)

    oauth = get_oauth()

    try:
        token = await oauth.google.authorize_access_token(
            request, code_verifier=code_verifier
        )
    except Exception:
        return _auth_redirect("oauth_failed")

    user_info = token.get("userinfo")
    if not user_info:
        return _auth_redirect("no_user_info")

    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")

    if not google_id or not email:
        return _auth_redirect("missing_info")

    ip_address = request.client.host if request.client else None

    try:
        login_response = await auth_service.authenticate_google(
            google_id=google_id,
            email=email,
            name=name,
            picture_url=picture,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    except HTTPException as e:
        error_msg = "account_not_found" if e.status_code == 403 else "auth_failed"
        return _auth_redirect(error_msg)

    frontend_url = _get_frontend_url()
    redirect = RedirectResponse(url=urllib.parse.urljoin(frontend_url, "/dashboard"), status_code=302)

    _set_auth_cookies(redirect, login_response.access_token, login_response.refresh_token)

    return redirect


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
    """Refresh access token using refresh token."""
    token = refresh_token_cookie
    if not token and body:
        token = body.refresh_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    ip_address = request.client.host if request.client else None
    token_response = await auth_service.refresh_access_token(
        token,
        user_agent=user_agent,
        ip_address=ip_address,
    )

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
) -> dict[str, str]:
    """Logout and revoke refresh token."""
    token = refresh_token_cookie
    if not token and body:
        token = body.refresh_token

    if token:
        ip_address = request.client.host if request.client else None
        await auth_service.logout(token, ip_address=ip_address, user_agent=user_agent)

    _clear_auth_cookies(response)

    return {"message": "Logout successful"}


@router.post("/logout-all")
@limiter.limit(AUTH_REFRESH_LIMIT)
async def logout_all_sessions(
    request: Request,
    response: Response,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, int]:
    """Logout all sessions for the current user."""
    count = await auth_service.logout_all_sessions(current_user.id)

    _clear_auth_cookies(response)

    return {"sessions_revoked": count}


@router.get("/me", response_model=UserInfo)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_current_user_info(
    request: Request,
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


# Profile Update Endpoints


@router.patch("/me", response_model=UserInfo)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def update_profile(
    request: Request,
    body: ProfileUpdateRequest,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
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


# Maximum avatar file size: 5MB
MAX_AVATAR_SIZE = 5 * 1024 * 1024


@router.post("/me/avatar", response_model=AvatarUploadResponse)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def upload_avatar(
    request: Request,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    file: UploadFile = File(...),
) -> AvatarUploadResponse:
    """Upload avatar image for current user."""
    content = await file.read(MAX_AVATAR_SIZE + 1)
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Avatar file too large. Maximum size: {MAX_AVATAR_SIZE // 1024 // 1024}MB",
        )

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
@limiter.limit(API_DEFAULT_LIMIT)
async def get_avatar(
    request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    """Get avatar image for a user. Requires authentication."""
    result = auth_service.get_avatar_file(user_id)
    if result is not None:
        content, content_type = result
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Avatar not found",
    )


@router.delete("/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def delete_avatar(
    request: Request,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """Delete current user's avatar."""
    await auth_service.delete_avatar(current_user.id)
    return None


# Notification Preferences Endpoints


@router.get("/me/notification-preferences", response_model=UserNotificationPreferencesResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_notification_preferences(
    request: Request,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserNotificationPreferencesResponse:
    """Get current user's notification preferences."""
    prefs = await auth_service.get_notification_preferences(current_user.id)

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
) -> UserNotificationPreferencesResponse:
    """Update current user's notification preferences (bulk)."""
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
    event_type: Annotated[str, Path(max_length=50, pattern=r"^[a-z_]+$")],
    body: UserNotificationPreferenceUpdate,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserNotificationPreferenceResponse:
    """Update a single notification preference."""
    if event_type not in EVENT_TYPE_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown event type",
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
