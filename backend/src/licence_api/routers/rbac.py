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
from licence_api.repositories.audit_repository import AuditRepository
from licence_api.repositories.permission_repository import PermissionRepository
from licence_api.repositories.role_repository import RoleRepository
from licence_api.repositories.user_repository import RefreshTokenRepository, UserRepository
from licence_api.security.auth import (
    Permissions,
    get_current_user,
    require_permission,
    require_superadmin,
)
from licence_api.security.password import get_password_service
from licence_api.security.rate_limit import limiter

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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserListResponse:
    """List all users with their roles."""
    user_repo = UserRepository(db)
    users = await user_repo.get_all_with_roles()

    items = []
    for user in users:
        roles = [r.code for r in user.roles]
        permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.code)

        items.append(
            UserInfo(
                id=user.id,
                email=user.email,
                name=user.name,
                picture_url=user.picture_url,
                auth_provider=user.auth_provider,
                is_active=user.is_active,
                require_password_change=user.require_password_change,
                roles=roles,
                permissions=sorted(permissions),
                last_login_at=user.last_login_at,
            )
        )

    return UserListResponse(items=items, total=len(items))


@router.post("/users", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def create_user(
    http_request: Request,
    request: UserCreateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_CREATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_agent: str | None = Header(default=None),
) -> UserInfo:
    """Create a new user with local authentication."""
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    audit_repo = AuditRepository(db)
    password_service = get_password_service()

    # Check if email already exists
    existing = await user_repo.get_by_email(request.email.lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Validate password
    is_valid, errors = password_service.validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=errors[0],
        )

    # Hash password
    password_hash = password_service.hash_password(request.password)

    # Create user
    user = await user_repo.create_user(
        email=request.email.lower(),
        password_hash=password_hash,
        name=request.name,
        auth_provider="local",
        require_password_change=True,  # Force password change on first login
    )

    # Assign roles
    if request.role_codes:
        roles = await role_repo.get_by_codes(request.role_codes)
        role_ids = [r.id for r in roles]
        await user_repo.set_roles(user.id, role_ids, assigned_by=current_user.id)

    # Audit log
    ip_address = http_request.client.host if http_request.client else None
    await audit_repo.log(
        action="create",
        resource_type="admin_user",
        resource_id=user.id,
        admin_user_id=current_user.id,
        changes={"email": user.email, "name": user.name, "roles": request.role_codes or []},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    await db.commit()

    # Fetch user with roles
    user = await user_repo.get_with_roles(user.id)
    roles = [r.code for r in user.roles]
    permissions = set()
    for role in user.roles:
        for perm in role.permissions:
            permissions.add(perm.code)

    return UserInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        auth_provider=user.auth_provider,
        is_active=user.is_active,
        require_password_change=user.require_password_change,
        roles=roles,
        permissions=sorted(permissions),
        last_login_at=user.last_login_at,
    )


@router.get("/users/{user_id}", response_model=UserInfo)
async def get_user(
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserInfo:
    """Get user by ID."""
    user_repo = UserRepository(db)
    user = await user_repo.get_with_roles(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    roles = [r.code for r in user.roles]
    permissions = set()
    for role in user.roles:
        for perm in role.permissions:
            permissions.add(perm.code)

    return UserInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        auth_provider=user.auth_provider,
        is_active=user.is_active,
        require_password_change=user.require_password_change,
        roles=roles,
        permissions=sorted(permissions),
        last_login_at=user.last_login_at,
    )


@router.put("/users/{user_id}", response_model=UserInfo)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserInfo:
    """Update user details."""
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)

    user = await user_repo.get_with_roles(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent deactivating yourself
    if request.is_active is False and user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    # Update fields
    if request.name is not None:
        user.name = request.name

    if request.is_active is not None:
        user.is_active = request.is_active

    # Update roles if provided and user has permission
    if request.role_codes is not None:
        if not current_user.has_permission(Permissions.USERS_MANAGE_ROLES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to manage roles",
            )

        # Prevent removing superadmin role from yourself
        if user_id == current_user.id and "superadmin" in current_user.roles:
            if "superadmin" not in request.role_codes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove superadmin role from yourself",
                )

        roles = await role_repo.get_by_codes(request.role_codes)
        role_ids = [r.id for r in roles]
        await user_repo.set_roles(user_id, role_ids, assigned_by=current_user.id)

    await db.commit()

    # Fetch updated user
    user = await user_repo.get_with_roles(user_id)
    roles = [r.code for r in user.roles]
    permissions = set()
    for role in user.roles:
        for perm in role.permissions:
            permissions.add(perm.code)

    return UserInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        auth_provider=user.auth_provider,
        is_active=user.is_active,
        require_password_change=user.require_password_change,
        roles=roles,
        permissions=sorted(permissions),
        last_login_at=user.last_login_at,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    http_request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_DELETE))],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_agent: str | None = Header(default=None),
) -> None:
    """Delete a user."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Audit log before deletion
    ip_address = http_request.client.host if http_request.client else None
    await audit_repo.log(
        action="delete",
        resource_type="admin_user",
        resource_id=user_id,
        admin_user_id=current_user.id,
        changes={"email": user.email},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    await db.delete(user)
    await db.commit()


@router.post("/users/{user_id}/reset-password")
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def reset_user_password(
    request: Request,
    user_id: UUID,
    body: PasswordResetRequest,
    current_user: Annotated[AdminUser, Depends(require_superadmin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_agent: str | None = Header(default=None),
) -> dict[str, str]:
    """Reset a user's password (superadmin only). Rate limited."""
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    password_service = get_password_service()

    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Validate password
    is_valid, errors = password_service.validate_password_strength(body.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=errors[0],
        )

    # Hash and update password
    password_hash = password_service.hash_password(body.new_password)
    await user_repo.update_password(
        user_id,
        password_hash,
        require_change=body.require_change,
    )

    # Revoke all sessions
    token_repo = RefreshTokenRepository(db)
    await token_repo.revoke_all_for_user(user_id)

    # Audit log
    ip_address = request.client.host if request.client else None
    await audit_repo.log(
        action="password_reset",
        resource_type="admin_user",
        resource_id=user_id,
        admin_user_id=current_user.id,
        changes={"target_email": user.email, "require_change": body.require_change},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    await db.commit()

    return {"message": "Password reset successfully"}


@router.post("/users/{user_id}/unlock")
@limiter.limit(ADMIN_SENSITIVE_LIMIT)
async def unlock_user(
    request: Request,
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.USERS_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Unlock a locked user account."""
    user_repo = UserRepository(db)

    user = await user_repo.unlock_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.commit()
    return {"message": "User unlocked successfully"}


@router.get("/users/{user_id}/sessions", response_model=list[SessionInfo])
async def get_user_sessions(
    user_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SessionInfo]:
    """Get active sessions for a user."""
    # Users can only view their own sessions unless they have permission
    if user_id != current_user.id:
        if not current_user.has_permission(Permissions.USERS_VIEW):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    token_repo = RefreshTokenRepository(db)
    sessions = await token_repo.get_active_sessions(user_id)

    return [
        SessionInfo(
            id=s.id,
            user_agent=s.user_agent,
            ip_address=s.ip_address,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_current=False,  # TODO: Compare with current token
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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoleListResponse:
    """List all roles with their permissions."""
    role_repo = RoleRepository(db)
    roles = await role_repo.get_all_with_permissions()

    items = [
        RoleResponse(
            id=r.id,
            code=r.code,
            name=r.name,
            description=r.description,
            is_system=r.is_system,
            priority=r.priority,
            permissions=[p.code for p in r.permissions],
        )
        for r in roles
    ]

    return RoleListResponse(items=items, total=len(items))


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_CREATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoleResponse:
    """Create a custom role."""
    role_repo = RoleRepository(db)
    permission_repo = PermissionRepository(db)

    # Check if role code already exists
    existing = await role_repo.get_by_code(request.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role code already exists",
        )

    # Create role
    role = await role_repo.create_role(
        code=request.code,
        name=request.name,
        description=request.description,
        is_system=False,
        priority=50,  # Default priority for custom roles
    )

    # Set permissions
    if request.permission_codes:
        permissions = await permission_repo.get_by_codes(request.permission_codes)
        permission_ids = [p.id for p in permissions]
        await role_repo.set_permissions(role.id, permission_ids)

    await db.commit()

    # Fetch updated role
    role = await role_repo.get_with_permissions(role.id)

    return RoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        priority=role.priority,
        permissions=[p.code for p in role.permissions],
    )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoleResponse:
    """Get role by ID."""
    role_repo = RoleRepository(db)
    role = await role_repo.get_with_permissions(role_id)

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    return RoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        priority=role.priority,
        permissions=[p.code for p in role.permissions],
    )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    request: RoleUpdateRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoleResponse:
    """Update a role."""
    role_repo = RoleRepository(db)
    permission_repo = PermissionRepository(db)

    role = await role_repo.get_with_permissions(role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # System roles can only have permissions changed by superadmin
    if role.is_system and not current_user.is_superadmin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can modify system roles",
        )

    # Update fields
    if request.name is not None:
        role.name = request.name

    if request.description is not None:
        role.description = request.description

    # Update permissions
    if request.permission_codes is not None:
        permissions = await permission_repo.get_by_codes(request.permission_codes)
        permission_ids = [p.id for p in permissions]
        await role_repo.set_permissions(role_id, permission_ids)

    await db.commit()

    # Fetch updated role
    role = await role_repo.get_with_permissions(role_id)

    return RoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        priority=role.priority,
        permissions=[p.code for p in role.permissions],
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.ROLES_DELETE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a custom role."""
    role_repo = RoleRepository(db)

    role = await role_repo.get_by_id(role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles",
        )

    await role_repo.delete_role(role_id)
    await db.commit()


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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PermissionListResponse:
    """List all permissions."""
    permission_repo = PermissionRepository(db)
    permissions = await permission_repo.get_all()

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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PermissionsByCategory]:
    """List all permissions grouped by category."""
    permission_repo = PermissionRepository(db)
    categories = await permission_repo.get_categories()

    result = []
    for category in categories:
        permissions = await permission_repo.get_by_category(category)
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
