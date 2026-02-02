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

    refresh_token: str = Field(max_length=2000)


class LocalLoginRequest(BaseModel):
    """Local login request."""

    email: EmailStr
    password: str = Field(min_length=8)


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str
    new_password: str = Field(min_length=12)


class PasswordResetRequest(BaseModel):
    """Password reset request (admin only)."""

    user_id: UUID
    new_password: str = Field(min_length=12)
    require_change: bool = True


class UserInfo(BaseModel):
    """User info DTO."""

    id: UUID
    email: EmailStr
    name: str | None = None
    picture_url: str | None = None
    auth_provider: str
    is_active: bool
    require_password_change: bool
    roles: list[str]
    permissions: list[str]
    is_superadmin: bool = False
    last_login_at: datetime | None = None
    # Locale preferences
    date_format: str | None = "DD.MM.YYYY"
    number_format: str | None = "de-DE"
    currency: str | None = "EUR"


class UserCreateRequest(BaseModel):
    """User creation request."""

    email: EmailStr
    name: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=12)
    role_codes: list[str] = Field(default=[], max_length=50)  # Max 50 roles per user


class UserUpdateRequest(BaseModel):
    """User update request."""

    name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    role_codes: list[str] | None = Field(default=None, max_length=50)  # Max 50 roles per user


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
    permission_codes: list[str] = Field(default=[], max_length=200)  # Max 200 permissions per role


class RoleUpdateRequest(BaseModel):
    """Role update request."""

    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    permission_codes: list[str] | None = Field(default=None, max_length=200)  # Max 200 permissions


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
    ip_address: str | None = Field(default=None, max_length=45)  # Max for IPv6
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
    slack_channel: str | None = Field(default=None, max_length=255)


class UserNotificationPreferenceUpdate(BaseModel):
    """User notification preference update request."""

    event_type: str = Field(max_length=100)
    enabled: bool = True
    slack_dm: bool = False
    slack_channel: str | None = Field(default=None, max_length=255)


class UserNotificationPreferenceBulkUpdate(BaseModel):
    """Bulk update notification preferences."""

    preferences: list[UserNotificationPreferenceUpdate] = Field(max_length=50)  # Max 50 event types


class UserNotificationPreferencesResponse(BaseModel):
    """User notification preferences response with available event types."""

    preferences: list[UserNotificationPreferenceResponse]
    available_event_types: list[NotificationEventType]


class ProfileUpdateRequest(BaseModel):
    """Profile update request for the current user."""

    name: str | None = Field(default=None, max_length=255)
    # Locale preferences
    date_format: str | None = Field(default=None, max_length=20)
    number_format: str | None = Field(default=None, max_length=20)
    currency: str | None = Field(default=None, max_length=10)


class AvatarUploadResponse(BaseModel):
    """Avatar upload response."""

    picture_url: str
    message: str = "Avatar uploaded successfully"
