"""External accounts router - Manage employee external provider links."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from licence_api.dependencies import get_external_account_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.external_account import (
    BulkLinkRequest,
    BulkLinkResponse,
    EmployeeSuggestion,
    ExternalAccountCreate,
    ExternalAccountListResponse,
    ExternalAccountResponse,
    SuggestionsRequest,
    SuggestionsResponse,
    UsernameMatchingSettingResponse,
    UsernameMatchingSettingUpdate,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import (
    API_DEFAULT_LIMIT,
    EXPENSIVE_READ_LIMIT,
    SENSITIVE_OPERATION_LIMIT,
    limiter,
)
from licence_api.services.external_account_service import ExternalAccountService

logger = logging.getLogger(__name__)
router = APIRouter()


# Settings endpoint
@router.get("/settings/username-matching", response_model=UsernameMatchingSettingResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_username_matching_setting(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_VIEW))],
    service: Annotated[ExternalAccountService, Depends(get_external_account_service)],
) -> UsernameMatchingSettingResponse:
    """Get username matching feature setting."""
    enabled = await service.is_username_matching_enabled()
    return UsernameMatchingSettingResponse(enabled=enabled)


@router.put("/settings/username-matching", response_model=UsernameMatchingSettingResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_username_matching_setting(
    request: Request,
    data: UsernameMatchingSettingUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[ExternalAccountService, Depends(get_external_account_service)],
) -> UsernameMatchingSettingResponse:
    """Update username matching feature setting."""
    enabled = await service.set_username_matching_enabled(
        enabled=data.enabled,
        user=current_user,
        request=request,
    )
    return UsernameMatchingSettingResponse(enabled=enabled)


# External accounts for a specific employee
@router.get(
    "/employees/{employee_id}/external-accounts",
    response_model=ExternalAccountListResponse,
)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_employee_external_accounts(
    request: Request,
    employee_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_VIEW))],
    service: Annotated[ExternalAccountService, Depends(get_external_account_service)],
) -> ExternalAccountListResponse:
    """Get all external accounts linked to an employee."""
    accounts = await service.get_employee_external_accounts(employee_id)
    return ExternalAccountListResponse(
        accounts=[
            ExternalAccountResponse(
                id=acc.id,
                employee_id=acc.employee_id,
                provider_type=acc.provider_type,
                external_username=acc.external_username,
                external_user_id=acc.external_user_id,
                display_name=acc.display_name,
                linked_at=acc.linked_at,
                linked_by_id=acc.linked_by_id,
                created_at=acc.created_at,
                updated_at=acc.updated_at,
            )
            for acc in accounts
        ],
        total=len(accounts),
    )


# Link an external account
@router.post(
    "/external-accounts",
    response_model=ExternalAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def link_external_account(
    request: Request,
    data: ExternalAccountCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_EDIT))],
    service: Annotated[ExternalAccountService, Depends(get_external_account_service)],
) -> ExternalAccountResponse:
    """Link an external account to an employee."""
    try:
        account = await service.link_account(
            employee_id=data.employee_id,
            provider_type=data.provider_type,
            external_username=data.external_username,
            external_user_id=data.external_user_id,
            display_name=data.display_name,
            user=current_user,
            request=request,
        )
        return ExternalAccountResponse(
            id=account.id,
            employee_id=account.employee_id,
            provider_type=account.provider_type,
            external_username=account.external_username,
            external_user_id=account.external_user_id,
            display_name=account.display_name,
            linked_at=account.linked_at,
            linked_by_id=account.linked_by_id,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
    except ValueError as e:
        logger.warning("Operation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to link external account",
        )


# Unlink an external account
@router.delete("/external-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def unlink_external_account(
    request: Request,
    account_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_EDIT))],
    service: Annotated[ExternalAccountService, Depends(get_external_account_service)],
) -> None:
    """Unlink an external account."""
    deleted = await service.unlink_account_by_id(
        account_id=account_id,
        user=current_user,
        request=request,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External account not found",
        )


# Get suggestions for linking
@router.get("/external-accounts/suggestions", response_model=SuggestionsResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_employee_suggestions(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_VIEW))],
    service: Annotated[ExternalAccountService, Depends(get_external_account_service)],
    display_name: str = Query(..., min_length=1, max_length=255),
    provider_type: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=5, ge=1, le=20),
) -> SuggestionsResponse:
    """Get employee suggestions for linking based on name similarity."""
    suggestions = await service.find_employee_suggestions(
        display_name=display_name,
        provider_type=provider_type,
        limit=limit,
    )
    return SuggestionsResponse(suggestions=[EmployeeSuggestion(**s) for s in suggestions])


# Bulk link accounts
@router.post("/external-accounts/bulk", response_model=BulkLinkResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def bulk_link_accounts(
    request: Request,
    data: BulkLinkRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_EDIT))],
    service: Annotated[ExternalAccountService, Depends(get_external_account_service)],
) -> BulkLinkResponse:
    """Bulk link multiple external accounts."""
    result = await service.bulk_link_accounts(
        links=data.links,
        user=current_user,
        request=request,
    )
    return BulkLinkResponse(
        linked=result["linked"],
        skipped=result["skipped"],
        errors=result["errors"],
    )


# Lookup by external username
@router.get("/external-accounts/lookup/{provider_type}/{username}")
@limiter.limit(API_DEFAULT_LIMIT)
async def lookup_by_external_username(
    request: Request,
    provider_type: Annotated[str, Path(max_length=50, pattern=r"^[a-z0-9_-]+$")],
    username: Annotated[str, Path(max_length=255, pattern=r"^[a-zA-Z0-9@._\-]+$")],
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.EMPLOYEES_VIEW))],
    service: Annotated[ExternalAccountService, Depends(get_external_account_service)],
) -> dict:
    """Lookup an employee by their external username."""
    employee = await service.get_employee_by_external_username(provider_type, username)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No employee linked to this username",
        )
    return {
        "employee_id": str(employee.id),
        "email": employee.email,
        "full_name": employee.full_name,
        "department": employee.department,
    }
