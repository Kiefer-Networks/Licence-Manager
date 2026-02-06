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

    refresh_token: str = Field(max_length=500)  # Tokens are typically ~86 bytes base64


class LocalLoginRequest(BaseModel):
    """Local login request."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class PasswordResetRequest(BaseModel):
    """Password reset request (admin only)."""

    user_id: UUID
    new_password: str = Field(min_length=12, max_length=128)
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
    totp_enabled: bool = False
    roles: list[str]
    permissions: list[str]
    is_superadmin: bool = False
    last_login_at: datetime | None = None
    # Locale preferences
    language: str = "en"  # ISO 639-1 language code (en, de)
    date_format: str | None = "DD.MM.YYYY"
    number_format: str | None = "de-DE"
    currency: str | None = "EUR"


class UserCreateRequest(BaseModel):
    """User creation request."""

    email: EmailStr
    name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=12)  # Optional when email is configured
    language: str = Field(
        default="en",
        min_length=2,
        max_length=5,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",  # ISO 639-1: en, de, or en-US, de-DE
    )
    role_codes: list[str] = Field(default=[], max_length=50)  # Max 50 roles per user


class UserUpdateRequest(BaseModel):
    """User update request."""

    email: EmailStr | None = None
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
    slack_channel: str | None = Field(
        default=None,
        max_length=80,  # Slack channel name limit
        pattern=r"^#?[a-z0-9][a-z0-9_-]{0,79}$",  # Slack channel format
    )


class UserNotificationPreferenceUpdate(BaseModel):
    """User notification preference update request."""

    event_type: str = Field(max_length=100)
    enabled: bool = True
    slack_dm: bool = False
    slack_channel: str | None = Field(
        default=None,
        max_length=80,  # Slack channel name limit
        pattern=r"^#?[a-z0-9][a-z0-9_-]{0,79}$",  # Slack channel format
    )


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
    # Locale preferences with validation patterns
    language: str | None = Field(
        default=None,
        min_length=2,
        max_length=5,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",  # ISO 639-1: en, de, or en-US, de-DE
    )
    date_format: str | None = Field(
        default=None,
        max_length=20,
        pattern=r"^[DMYdmy.\-/\s]+$",  # Allow common date format chars: D, M, Y, separators
    )
    number_format: str | None = Field(
        default=None,
        max_length=20,
        pattern=r"^[a-z]{2}-[A-Z]{2}$",  # BCP 47 locale format: xx-XX (e.g., de-DE, en-US)
    )
    currency: str | None = Field(
        default=None,
        max_length=3,
        min_length=3,
        pattern=r"^[A-Z]{3}$",  # ISO 4217 currency codes: exactly 3 uppercase letters
    )


class AvatarUploadResponse(BaseModel):
    """Avatar upload response."""

    picture_url: str
    message: str = "Avatar uploaded successfully"


# TOTP Two-Factor Authentication DTOs


class TotpSetupResponse(BaseModel):
    """TOTP setup response with QR code and secret."""

    secret: str = Field(description="Base32-encoded TOTP secret for manual entry")
    qr_code_data_uri: str = Field(description="QR code as data URI for display")
    provisioning_uri: str = Field(description="OTPAuth URI for authenticator apps")


class TotpVerifyRequest(BaseModel):
    """TOTP verification request."""

    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit TOTP code from authenticator app",
    )


class TotpEnableResponse(BaseModel):
    """Response after successfully enabling TOTP."""

    enabled: bool = True
    backup_codes: list[str] = Field(description="Single-use backup codes for recovery")
    message: str = "Two-factor authentication enabled successfully"


class TotpDisableRequest(BaseModel):
    """Request to disable TOTP (requires current password)."""

    password: str = Field(
        min_length=1, max_length=128, description="Current password for verification"
    )


class TotpStatusResponse(BaseModel):
    """TOTP status for current user."""

    enabled: bool
    verified_at: datetime | None = None
    backup_codes_remaining: int = 0


class TotpLoginRequest(BaseModel):
    """Login request with TOTP code."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    totp_code: str | None = Field(
        default=None,
        min_length=6,
        max_length=10,  # Allow backup codes (8 chars + dash)
        description="6-digit TOTP code or backup code",
    )


class TotpRequiredResponse(BaseModel):
    """Response indicating TOTP verification is required."""

    totp_required: bool = True
    message: str = "Two-factor authentication required"


class TotpBackupCodesResponse(BaseModel):
    """Response with regenerated backup codes."""

    backup_codes: list[str] = Field(description="New single-use backup codes")
    message: str = "Backup codes regenerated successfully"


class LoginResponse(BaseModel):
    """Extended login response that may require TOTP."""

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    totp_required: bool = False


class UserCreateResponse(BaseModel):
    """User creation response."""

    user: UserInfo
    password_sent_via_email: bool = False
    temporary_password: str | None = None  # Only returned if email not configured


class PasswordResetResponse(BaseModel):
    """Password reset response."""

    message: str = "Password reset successfully"
    password_sent_via_email: bool = False
    temporary_password: str | None = None  # Only returned if email not configured
