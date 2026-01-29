"""Authentication DTOs."""

from pydantic import BaseModel, EmailStr

from licence_api.models.domain.admin_user import UserRole


class TokenResponse(BaseModel):
    """Token response DTO."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """User info DTO."""

    email: EmailStr
    name: str | None = None
    picture_url: str | None = None
    role: UserRole
