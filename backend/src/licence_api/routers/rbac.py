"""RBAC router for user, role, and permission management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.auth import (
    PasswordResetRequest,
    PermissionResponse,
    PermissionsByCategory,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    SessionInfo,
    UserCreateRequest,
    UserInfo,
    UserUpdateRequest,
)
from licence_api.security.auth import (
    Permissions,
    get_current_user,
    require_permission,
    require_superadmin,
)
from licence_api.security.rate_limit import limiter
from licence_api.services.rbac_service import RbacService

router = APIRouter()

# Rate limit for sensitive operations
ADMIN_SENSITIVE_LIMIT = "5/minute"


def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RbacService:
    """Get RbacService instance."""
    return RbacService(db)


# ============================================================================
# User Management
# ============================================================================


class UserListResponse(BaseModel):
    """User list response."""

    items: list[UserInfo]
    total: int


@router.get("/users", response_model=UserListResponse)
async def list_users(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_VIEW))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> UserListResponse:
    """List all users with their roles."""
    items = await service.list_users()
    return UserListResponse(items=items, total=len(items))


@router.post("/users", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def create_user(
    http_request: Request,
    request: UserCreateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_CREATE))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    user_agent: str | None = Header(default=None),
) -> UserInfo:
    """Create a new user with local authentication."""
    try:
        return await service.create_user(
            request=request,
            current_user=current_user,
            http_request=http_request,
            user_agent=user_agent,
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "already registered" in error_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users/{user_id}", response_model=UserInfo)
async def get_user(
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_VIEW))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> UserInfo:
    """Get user by ID."""
    user_info = await service.get_user(user_id)
    if user_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_info


@router.put("/users/{user_id}", response_model=UserInfo)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_EDIT))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> UserInfo:
    """Update user details."""
    # Check role management permission
    if request.role_codes is not None:
        if not current_user.has_permission(Permissions.USERS_MANAGE_ROLES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to manage roles",
            )

    try:
        return await service.update_user(
            user_id=user_id,
            request=request,
            current_user=current_user,
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    http_request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_DELETE))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    user_agent: str | None = Header(default=None),
) -> None:
    """Delete a user."""
    try:
        await service.delete_user(
            user_id=user_id,
            current_user=current_user,
            http_request=http_request,
            user_agent=user_agent,
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/reset-password")
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def reset_user_password(
    request: Request,
    user_id: UUID,
    body: PasswordResetRequest,
    current_user: Annotated[AdminUser, Depends(require_superadmin)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    user_agent: str | None = Header(default=None),
) -> dict[str, str]:
    """Reset a user's password (superadmin only). Rate limited."""
    try:
        await service.reset_user_password(
            user_id=user_id,
            body=body,
            current_user=current_user,
            http_request=request,
            user_agent=user_agent,
        )
        return {"message": "Password reset successfully"}
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/unlock")
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def unlock_user(
    request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_EDIT))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> dict[str, str]:
    """Unlock a locked user account."""
    try:
        await service.unlock_user(user_id)
        return {"message": "User unlocked successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/users/{user_id}/sessions", response_model=list[SessionInfo])
async def get_user_sessions(
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> list[SessionInfo]:
    """Get active sessions for a user."""
    # Users can only view their own sessions unless they have permission
    if user_id != current_user.id:
        if not current_user.has_permission(Permissions.USERS_VIEW):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    sessions = await service.get_user_sessions(user_id)

    return [
        SessionInfo(
            id=s.id,
            user_agent=s.user_agent,
            ip_address=s.ip_address,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_current=False,
        )
        for s in sessions
    ]


# ============================================================================
# Role Management
# ============================================================================


class RoleListResponse(BaseModel):
    """Role list response."""

    items: list[RoleResponse]
    total: int


@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_VIEW))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> RoleListResponse:
    """List all roles with their permissions."""
    items = await service.list_roles()
    return RoleListResponse(items=items, total=len(items))


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_CREATE))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> RoleResponse:
    """Create a custom role."""
    try:
        return await service.create_role(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_VIEW))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> RoleResponse:
    """Get role by ID."""
    role = await service.get_role(role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    request: RoleUpdateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_EDIT))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> RoleResponse:
    """Update a role."""
    try:
        return await service.update_role(
            role_id=role_id,
            request=request,
            current_user=current_user,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_DELETE))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> None:
    """Delete a custom role."""
    try:
        await service.delete_role(role_id)
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Permission Management
# ============================================================================


class PermissionListResponse(BaseModel):
    """Permission list response."""

    items: list[PermissionResponse]
    total: int


@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_VIEW))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> PermissionListResponse:
    """List all permissions."""
    permissions = await service.list_permissions()

    items = [
        PermissionResponse(
            id=p.id,
            code=p.code,
            name=p.name,
            description=p.description,
            category=p.category,
        )
        for p in permissions
    ]

    return PermissionListResponse(items=items, total=len(items))


@router.get("/permissions/by-category", response_model=list[PermissionsByCategory])
async def list_permissions_by_category(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_VIEW))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> list[PermissionsByCategory]:
    """List all permissions grouped by category."""
    categories = await service.get_permission_categories()

    result = []
    for category in categories:
        permissions = await service.get_permissions_by_category(category)
        result.append(
            PermissionsByCategory(
                category=category,
                permissions=[
                    PermissionResponse(
                        id=p.id,
                        code=p.code,
                        name=p.name,
                        description=p.description,
                        category=p.category,
                    )
                    for p in permissions
                ],
            )
        )

    return result
