"""Authentication router."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.dto.auth import TokenResponse, UserInfo
from licence_api.models.domain.admin_user import AdminUser
from licence_api.security.auth import get_current_user
from licence_api.services.user_service import UserService

router = APIRouter()


class GoogleAuthRequest(BaseModel):
    """Google authentication request."""

    id_token: str


@router.post("/google", response_model=TokenResponse)
async def authenticate_with_google(
    request: GoogleAuthRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate with Google OAuth.

    Exchange a Google ID token for a JWT access token.
    First user to authenticate becomes an admin.
    """
    service = UserService(db)
    return await service.authenticate_with_google(request.id_token)


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserInfo:
    """Get current user information."""
    service = UserService(db)
    user_info = await service.get_user_info(current_user.id)
    if user_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user_info


@router.post("/logout")
async def logout() -> dict[str, str]:
    """Logout current user.

    Note: JWT tokens are stateless. Client should discard the token.
    """
    return {"message": "Logout successful"}
