"""Authentication router."""

import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, File, Header, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.config import get_settings
from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.auth import (
    AvatarUploadResponse,
    LocalLoginRequest,
    NotificationEventType,
    PasswordChangeRequest,
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
from licence_api.security.csrf import generate_csrf_token, validate_csrf
from licence_api.security.rate_limit import (
    AUTH_LOGIN_LIMIT,
    AUTH_LOGOUT_LIMIT,
    AUTH_PASSWORD_CHANGE_LIMIT,
    AUTH_REFRESH_LIMIT,
    limiter,
)
from licence_api.services.auth_service import AuthService
from licence_api.repositories.user_repository import UserRepository
from licence_api.repositories.user_notification_preference_repository import UserNotificationPreferenceRepository
from licence_api.utils.file_validation import (
    validate_image_signature,
    get_extension_from_content_type,
)


# Dependency injection functions
def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get UserRepository instance."""
    return UserRepository(db)


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get AuthService instance."""
    return AuthService(db)

logger = logging.getLogger(__name__)

# Avatar storage directory for admin users
ADMIN_AVATAR_DIR = Path(__file__).parent.parent.parent.parent / "data" / "admin_avatars"
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

router = APIRouter()

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


# Profile Update Endpoints


@router.patch("/me", response_model=UserInfo)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserInfo:
    """Update current user's profile (name)."""
    # Update name if provided via repository
    if body.name is not None:
        await user_repo.update_name(current_user.id, body.name if body.name else None)
        await db.commit()

    # Return updated user info
    user_info = await auth_service.get_user_info(current_user.id)
    if user_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user_info


@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    file: UploadFile = File(...),
) -> AvatarUploadResponse:
    """Upload avatar image for current user."""
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_AVATAR_SIZE // (1024 * 1024)} MB",
        )

    # Validate file signature (magic bytes) to prevent content-type spoofing
    if not validate_image_signature(content, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match declared file type",
        )

    # Ensure avatar directory exists
    ADMIN_AVATAR_DIR.mkdir(parents=True, exist_ok=True)

    # Generate unique filename with extension
    ext = get_extension_from_content_type(file.content_type)

    filename = f"{current_user.id}{ext}"
    file_path = ADMIN_AVATAR_DIR / filename

    # Remove old avatar with different extension if exists
    for old_ext in [".jpg", ".png", ".gif", ".webp"]:
        old_file = ADMIN_AVATAR_DIR / f"{current_user.id}{old_ext}"
        if old_file.exists() and old_file != file_path:
            try:
                old_file.unlink()
            except OSError as e:
                logger.warning(f"Failed to delete old avatar file: {e}")

    # Write new avatar
    try:
        file_path.write_bytes(content)
    except Exception as e:
        logger.error(f"Failed to write avatar file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save avatar",
        )

    # Update picture_url in database via repository
    picture_url = f"/api/v1/auth/avatar/{current_user.id}"
    await user_repo.update_avatar(current_user.id, picture_url)
    await db.commit()

    return AvatarUploadResponse(picture_url=picture_url)


@router.get("/avatar/{user_id}")
async def get_avatar(
    user_id: str,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
) -> Response:
    """Get avatar image for a user. Requires authentication."""
    # Validate user_id to prevent path traversal
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

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
async def delete_avatar(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> dict[str, str]:
    """Delete current user's avatar."""
    # Remove avatar files
    for ext in [".jpg", ".png", ".gif", ".webp"]:
        file_path = ADMIN_AVATAR_DIR / f"{current_user.id}{ext}"
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError as e:
                logger.warning(f"Failed to delete avatar file: {e}")

    # Clear picture_url in database via repository
    await user_repo.update_avatar(current_user.id, None)
    await db.commit()

    return {"message": "Avatar deleted successfully"}


# Notification Preferences Endpoints


@router.get("/me/notification-preferences", response_model=UserNotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserNotificationPreferencesResponse:
    """Get current user's notification preferences."""
    repo = UserNotificationPreferenceRepository(db)
    prefs = await repo.get_by_user_id(current_user.id)

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
async def update_notification_preferences(
    body: UserNotificationPreferenceBulkUpdate,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserNotificationPreferencesResponse:
    """Update current user's notification preferences (bulk)."""
    repo = UserNotificationPreferenceRepository(db)

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

    prefs = await repo.bulk_upsert(current_user.id, prefs_data)
    await db.commit()

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


@router.patch("/me/notification-preferences/{event_type}", response_model=UserNotificationPreferenceResponse)
async def update_single_notification_preference(
    event_type: str,
    body: UserNotificationPreferenceUpdate,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserNotificationPreferenceResponse:
    """Update a single notification preference."""
    if event_type not in EVENT_TYPE_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown event type: {event_type}",
        )

    repo = UserNotificationPreferenceRepository(db)
    pref = await repo.upsert(
        user_id=current_user.id,
        event_type=event_type,
        enabled=body.enabled,
        slack_dm=body.slack_dm,
        slack_channel=body.slack_channel,
    )
    await db.commit()

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
