"""User service for authentication and user management."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.admin_user import AdminUser, UserRole
from licence_api.models.dto.auth import TokenResponse, UserInfo
from licence_api.repositories.user_repository import UserRepository
from licence_api.security.auth import create_access_token, verify_google_token


class UserService:
    """Service for user authentication and management."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.user_repo = UserRepository(session)

    async def authenticate_with_google(self, google_token: str) -> TokenResponse:
        """Authenticate user with Google OAuth token.

        Args:
            google_token: Google ID token

        Returns:
            TokenResponse with JWT access token

        Raises:
            HTTPException: If authentication fails
        """
        # Verify Google token
        token_info = await verify_google_token(google_token)

        # Check if this is the first user (make them admin)
        admin_count = await self.user_repo.count_admins()
        is_first_user = admin_count == 0
        role = "admin" if is_first_user else "viewer"

        # Create or update user
        user = await self.user_repo.create_or_update(
            email=token_info.email,
            name=token_info.name,
            picture_url=token_info.picture,
            role=role,
        )

        # Create JWT token
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=UserRole(user.role),
        )

        from licence_api.config import get_settings
        settings = get_settings()

        return TokenResponse(
            access_token=access_token,
            expires_in=settings.jwt_expiration_hours * 3600,
        )

    async def get_user_info(self, user_id: UUID) -> UserInfo | None:
        """Get user info by ID.

        Args:
            user_id: User UUID

        Returns:
            UserInfo or None if not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            return None

        return UserInfo(
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
            role=UserRole(user.role),
        )

    async def get_user_by_email(self, email: str) -> AdminUser | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            AdminUser or None if not found
        """
        user = await self.user_repo.get_by_email(email)
        if user is None:
            return None

        return AdminUser(
            id=user.id,
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
            role=UserRole(user.role),
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def update_user_role(self, user_id: UUID, role: UserRole) -> AdminUser | None:
        """Update user role.

        Args:
            user_id: User UUID
            role: New role

        Returns:
            Updated AdminUser or None if not found
        """
        user = await self.user_repo.update(user_id, role=role.value)
        if user is None:
            return None

        return AdminUser(
            id=user.id,
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
            role=UserRole(user.role),
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def list_users(self) -> list[AdminUser]:
        """List all admin users.

        Returns:
            List of AdminUser
        """
        users = await self.user_repo.get_all()
        return [
            AdminUser(
                id=user.id,
                email=user.email,
                name=user.name,
                picture_url=user.picture_url,
                role=UserRole(user.role),
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            for user in users
        ]
