"""RBAC router for user, role, and permission management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
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
from licence_api.security.rate_limit import API_DEFAULT_LIMIT, EXPENSIVE_READ_LIMIT, limiter
from licence_api.services.rbac_service import RbacService
from licence_api.utils.errors import (
    raise_bad_request,
    raise_conflict,
    raise_forbidden,
    raise_not_found,
)

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
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_users(
    request: Request,
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
    user_agent: str | None = Header(default=None),
) -> UserCreateResponse:
    """Create a new user for Google OAuth login.

    Users are created with email and roles only - they authenticate via Google.
    """
    try:
        return await service.create_user(
            request=body,
            current_user=current_user,
            http_request=request,
            user_agent=user_agent,
        )
    except UserAlreadyExistsError:
        raise_conflict("Email already registered")
    except ValidationError as e:
        raise_bad_request(str(e))


@router.get("/users/{user_id}", response_model=UserInfo)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_user(
    request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_VIEW))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> UserInfo:
    """Get user by ID."""
    user_info = await service.get_user(user_id)
    if user_info is None:
        raise_not_found("User not found")
    return user_info


@router.put("/users/{user_id}", response_model=UserInfo)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def update_user(
    request: Request,
    user_id: UUID,
    body: UserUpdateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_EDIT))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> UserInfo:
    """Update user details."""
    if body.role_codes is not None:
        if not current_user.has_permission(Permissions.USERS_MANAGE_ROLES):
            raise_forbidden("Insufficient permissions to manage roles")

    try:
        return await service.update_user(
            user_id=user_id,
            request=body,
            current_user=current_user,
        )
    except UserNotFoundError:
        raise_not_found("User not found")
    except UserAlreadyExistsError:
        raise_conflict("Email already registered")
    except ValidationError as e:
        raise_bad_request(str(e))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def delete_user(
    request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_superadmin)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
    user_agent: str | None = Header(default=None),
) -> None:
    """Delete a user. Superadmin only."""
    try:
        await service.delete_user(
            user_id=user_id,
            current_user=current_user,
            http_request=request,
            user_agent=user_agent,
        )
    except UserNotFoundError:
        raise_not_found("User not found")
    except CannotDeleteSelfError:
        raise_bad_request("Cannot delete your own account")


@router.get("/users/{user_id}/sessions", response_model=list[SessionInfo])
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_user_sessions(
    request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> list[SessionInfo]:
    """Get active sessions for a user."""
    is_own_sessions = user_id == current_user.id
    has_view_permission = current_user.has_permission(Permissions.USERS_VIEW)

    if not is_own_sessions and not has_view_permission:
        raise_forbidden("Viewing other users' sessions requires users.view permission")

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
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_roles(
    request: Request,
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
) -> RoleResponse:
    """Create a custom role."""
    try:
        return await service.create_role(body)
    except RoleAlreadyExistsError:
        raise_conflict("Role already exists")
    except ValidationError:
        raise_bad_request("Invalid role data")


@router.get("/roles/{role_id}", response_model=RoleResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_role(
    request: Request,
    role_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_VIEW))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> RoleResponse:
    """Get role by ID."""
    role = await service.get_role(role_id)
    if role is None:
        raise_not_found("Role not found")
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def update_role(
    request: Request,
    role_id: UUID,
    body: RoleUpdateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_EDIT))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> RoleResponse:
    """Update a role."""
    try:
        return await service.update_role(
            role_id=role_id,
            request=body,
            current_user=current_user,
        )
    except RoleNotFoundError:
        raise_not_found("Role not found")
    except CannotModifySystemRoleError:
        raise_forbidden("Cannot modify system role")


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def delete_role(
    request: Request,
    role_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_DELETE))],
    service: Annotated[RbacService, Depends(get_rbac_service)],
) -> None:
    """Delete a custom role."""
    try:
        await service.delete_role(role_id)
    except RoleNotFoundError:
        raise_not_found("Role not found")
    except CannotModifySystemRoleError:
        raise_forbidden("Cannot delete system role")
    except RoleHasUsersError as e:
        user_count = e.details.get("user_count", 0)
        raise_conflict(f"Cannot delete role with assigned users ({user_count} users)")


# ============================================================================
# Permission Management
# ============================================================================


class PermissionListResponse(BaseModel):
    """Permission list response."""

    items: list[PermissionResponse]
    total: int


@router.get("/permissions", response_model=PermissionListResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_permissions(
    request: Request,
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
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_permissions_by_category(
    request: Request,
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
