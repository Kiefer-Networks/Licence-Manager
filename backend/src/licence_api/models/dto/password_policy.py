"""Password policy DTOs."""

from pydantic import BaseModel, Field, model_validator


class PasswordPolicySettings(BaseModel):
    """Password policy configuration settings."""

    # Length requirements
    min_length: int = Field(default=12, ge=8, le=128, description="Minimum password length")

    # Complexity requirements
    require_uppercase: bool = Field(default=True, description="Require uppercase letters")
    require_lowercase: bool = Field(default=True, description="Require lowercase letters")
    require_numbers: bool = Field(default=True, description="Require numeric digits")
    require_special_chars: bool = Field(default=True, description="Require special characters")

    # Expiration and history
    expiry_days: int = Field(
        default=90, ge=0, le=365, description="Password expiry in days (0 = never)"
    )
    history_count: int = Field(
        default=5, ge=0, le=24, description="Number of previous passwords to check"
    )

    # Lockout settings
    max_failed_attempts: int = Field(
        default=5, ge=1, le=20, description="Max failed attempts before lockout"
    )
    lockout_duration_minutes: int = Field(
        default=15, ge=1, le=1440, description="Lockout duration in minutes"
    )

    @model_validator(mode="after")
    def validate_min_length_warning(self) -> "PasswordPolicySettings":
        """Validate minimum length - allow but warn for < 16."""
        # Validation happens at API level, this just ensures bounds
        if self.min_length < 8:
            raise ValueError("Minimum password length cannot be less than 8 characters")
        return self


class PasswordPolicyResponse(PasswordPolicySettings):
    """Password policy response with warning flag."""

    length_warning: bool = Field(
        default=False, description="True if min_length < 16 (recommended minimum)"
    )

    @model_validator(mode="after")
    def set_length_warning(self) -> "PasswordPolicyResponse":
        """Set warning flag if length is below recommended."""
        self.length_warning = self.min_length < 16
        return self


class PasswordValidationRequest(BaseModel):
    """Request to validate a password against policy."""

    password: str = Field(..., min_length=1, description="Password to validate")


class PasswordValidationResponse(BaseModel):
    """Password validation result."""

    valid: bool = Field(..., description="Whether password meets policy requirements")
    errors: list[str] = Field(default_factory=list, description="List of validation errors")
    strength: str = Field(
        default="weak", description="Password strength: weak, medium, strong, very_strong"
    )
