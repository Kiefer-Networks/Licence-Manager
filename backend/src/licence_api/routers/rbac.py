"""RBAC router for user, role, and permission management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from licence_api.dependencies import get_rbac_service
from licence_api.exceptions import (
    CannotDeleteSelfError,
    CannotModifySystemRoleError,
    RoleAlreadyExistsError,
    RoleHasUsersError,
    RoleNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.auth import (
    PasswordResetResponse,
    PermissionResponse,
    PermissionsByCategory,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    SessionInfo,
    UserCreateRequest,
    UserCreateResponse,
    UserInfo,
    UserUpdateRequest,
)
from licence_api.security.auth import (
    Permissions,
    get_current_user,
    require_permission,
    require_superadmin,
)
from licence_api.security.csrf import CSRFProtected
from licence_api.security.rate_limit import limiter
from licence_api.services.rbac_service import RbacService

router = APIRouter()

# Rate limit for sensitive operations
ADMIN_SENSITIVE_LIMIT = "5/minute"


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


@router.post("/users", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def create_user(
    request: Request,
    body: UserCreateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_CREATE))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    user_agent: str | None = Header(default=None),
) -> UserCreateResponse:
    """Create a new user with local authentication.

    If email is configured, password can be omitted and will be auto-generated
    and sent via email. If email is not configured, password is required.
    """
    try:
        return await service.create_user(
            request=body,
            current_user=current_user,
            http_request=request,
            user_agent=user_agent,
        )
    except UserAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    except ValidationError as e:
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
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def update_user(
    request: Request,
    user_id: UUID,
    body: UserUpdateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_EDIT))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> UserInfo:
    """Update user details."""
    # Check role management permission
    if body.role_codes is not None:
        if not current_user.has_permission(Permissions.USERS_MANAGE_ROLES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to manage roles",
            )

    try:
        return await service.update_user(
            user_id=user_id,
            request=body,
            current_user=current_user,
        )
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid update data")


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def delete_user(
    request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_superadmin)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    user_agent: str | None = Header(default=None),
) -> None:
    """Delete a user. Superadmin only - user deletion is a critical operation."""
    try:
        await service.delete_user(
            user_id=user_id,
            current_user=current_user,
            http_request=request,
            user_agent=user_agent,
        )
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    except CannotDeleteSelfError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResponse)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def reset_user_password(
    request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_superadmin)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    user_agent: str | None = Header(default=None),
) -> PasswordResetResponse:
    """Reset a user's password (superadmin only). Rate limited.

    Generates a new temporary password. If email is configured, the password
    is sent via email. Otherwise, it is returned in the response.
    """
    try:
        return await service.reset_user_password(
            user_id=user_id,
            current_user=current_user,
            http_request=request,
            user_agent=user_agent,
        )
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.post("/users/{user_id}/unlock")
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def unlock_user(
    request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_EDIT))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> dict[str, str]:
    """Unlock a locked user account."""
    try:
        await service.unlock_user(user_id)
        return {"message": "User unlocked successfully"}
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get("/users/{user_id}/sessions", response_model=list[SessionInfo])
async def get_user_sessions(
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> list[SessionInfo]:
    """Get active sessions for a user.

    Permission requirements:
    - Users can always view their own sessions (user_id == current_user.id)
    - Viewing other users' sessions requires users.view permission

    Args:
        user_id: The UUID of the user whose sessions to retrieve
        current_user: The authenticated user making the request
        service: The RBAC service instance

    Returns:
        List of active sessions for the specified user

    Raises:
        HTTPException 403: If attempting to view another user's sessions without
            the required users.view permission
    """
    # Verify permission: users can view own sessions, others require users.view
    is_own_sessions = user_id == current_user.id
    has_view_permission = current_user.has_permission(Permissions.USERS_VIEW)

    if not is_own_sessions and not has_view_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewing other users' sessions requires users.view permission",
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
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def create_role(
    request: Request,
    body: RoleCreateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_CREATE))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> RoleResponse:
    """Create a custom role."""
    try:
        return await service.create_role(body)
    except RoleAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role data")


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
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def update_role(
    request: Request,
    role_id: UUID,
    body: RoleUpdateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_EDIT))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> RoleResponse:
    """Update a role."""
    try:
        return await service.update_role(
            role_id=role_id,
            request=body,
            current_user=current_user,
        )
    except RoleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    except CannotModifySystemRoleError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system role"
        )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def delete_role(
    request: Request,
    role_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_DELETE))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> None:
    """Delete a custom role."""
    try:
        await service.delete_role(role_id)
    except RoleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    except CannotModifySystemRoleError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system role"
        )
    except RoleHasUsersError as e:
        user_count = e.details.get("user_count", 0)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete role with assigned users ({user_count} users)",
        )


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
