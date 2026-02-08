"""Authentication DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    """Token response DTO."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(max_length=500)


class UserInfo(BaseModel):
    """User info DTO."""

    id: UUID
    email: EmailStr
    name: str | None = None
    picture_url: str | None = None
    auth_provider: str = "google"
    is_active: bool
    roles: list[str]
    permissions: list[str]
    is_superadmin: bool = False
    last_login_at: datetime | None = None
    # Locale preferences
    language: str = "en"
    date_format: str | None = "DD.MM.YYYY"
    number_format: str | None = "de-DE"
    currency: str | None = "EUR"


class UserCreateRequest(BaseModel):
    """User creation request (Google OAuth only - no password needed)."""

    email: EmailStr
    name: str | None = Field(default=None, max_length=255)
    language: str = Field(
        default="en",
        min_length=2,
        max_length=5,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
    )
    role_codes: list[str] = Field(default=[], max_length=50)


class UserCreateResponse(BaseModel):
    """User creation response."""

    user: UserInfo


class UserUpdateRequest(BaseModel):
    """User update request."""

    email: EmailStr | None = None
    name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    role_codes: list[str] | None = Field(default=None, max_length=50)


class RoleResponse(BaseModel):
    """Role response DTO."""

    id: UUID
    code: str
    name: str
    description: str | None = None
    is_system: bool
    priority: int
    permissions: list[str]


class RoleCreateRequest(BaseModel):
    """Role creation request."""

    code: str = Field(min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    permission_codes: list[str] = Field(default=[], max_length=200)


class RoleUpdateRequest(BaseModel):
    """Role update request."""

    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    permission_codes: list[str] | None = Field(default=None, max_length=200)


class PermissionResponse(BaseModel):
    """Permission response DTO."""

    id: UUID
    code: str
    name: str
    description: str | None = None
    category: str


class PermissionsByCategory(BaseModel):
    """Permissions grouped by category."""

    category: str
    permissions: list[PermissionResponse]


class SessionInfo(BaseModel):
    """Active session info."""

    id: UUID
    user_agent: str | None = Field(default=None, max_length=1000)
    ip_address: str | None = Field(default=None, max_length=45)
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


# User Notification Preferences DTOs


class NotificationEventType(BaseModel):
    """Notification event type info."""

    code: str
    name: str
    description: str
    category: str


class UserNotificationPreferenceResponse(BaseModel):
    """User notification preference response."""

    id: UUID
    event_type: str
    event_name: str
    event_description: str
    enabled: bool
    slack_dm: bool
    slack_channel: str | None = Field(
        default=None,
        max_length=80,
        pattern=r"^#?[a-z0-9][a-z0-9_-]{0,79}$",
    )


class UserNotificationPreferenceUpdate(BaseModel):
    """User notification preference update request."""

    event_type: str = Field(max_length=100)
    enabled: bool = True
    slack_dm: bool = False
    slack_channel: str | None = Field(
        default=None,
        max_length=80,
        pattern=r"^#?[a-z0-9][a-z0-9_-]{0,79}$",
    )


class UserNotificationPreferenceBulkUpdate(BaseModel):
    """Bulk update notification preferences."""

    preferences: list[UserNotificationPreferenceUpdate] = Field(max_length=50)


class UserNotificationPreferencesResponse(BaseModel):
    """User notification preferences response with available event types."""

    preferences: list[UserNotificationPreferenceResponse]
    available_event_types: list[NotificationEventType]


class ProfileUpdateRequest(BaseModel):
    """Profile update request for the current user."""

    name: str | None = Field(default=None, max_length=255)
    language: str | None = Field(
        default=None,
        min_length=2,
        max_length=5,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
    )
    date_format: str | None = Field(
        default=None,
        max_length=20,
        pattern=r"^[DMYdmy.\-/\s]+$",
    )
    number_format: str | None = Field(
        default=None,
        max_length=20,
        pattern=r"^[a-z]{2}-[A-Z]{2}$",
    )
    currency: str | None = Field(
        default=None,
        max_length=3,
        min_length=3,
        pattern=r"^[A-Z]{3}$",
    )


class AvatarUploadResponse(BaseModel):
    """Avatar upload response."""

    picture_url: str
    message: str = "Avatar uploaded successfully"


class LoginResponse(BaseModel):
    """Login response for Google OAuth."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
