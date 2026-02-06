"""Payment methods router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from pydantic import BaseModel

from licence_api.models.dto.payment_method import (
    PaymentMethodCreate,
    PaymentMethodListResponse,
    PaymentMethodResponse,
    PaymentMethodUpdate,
)


class PaymentMethodUsageResponse(BaseModel):
    """Response showing which providers use a payment method."""

    payment_method_id: str
    provider_count: int
    providers: list[dict]  # List of {id, name, display_name}
from licence_api.security.auth import require_permission, Permissions
from licence_api.security.csrf import CSRFProtected
from licence_api.security.rate_limit import limiter, SENSITIVE_OPERATION_LIMIT
from licence_api.services.payment_method_service import PaymentMethodService

router = APIRouter()


def get_payment_method_service(
    db: AsyncSession = Depends(get_db),
) -> PaymentMethodService:
    """Get PaymentMethodService instance."""
    return PaymentMethodService(db)


@router.get("", response_model=PaymentMethodListResponse)
async def list_payment_methods(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PAYMENT_METHODS_VIEW))],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
) -> PaymentMethodListResponse:
    """List all payment methods."""
    return await service.list_payment_methods()


@router.post("", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_payment_method(
    request: Request,
    data: PaymentMethodCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PAYMENT_METHODS_CREATE))],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> PaymentMethodResponse:
    """Create a new payment method. Requires payment_methods.create permission."""
    try:
        return await service.create_payment_method(
            data=data,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment method data",
        )


@router.get("/{payment_method_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    payment_method_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PAYMENT_METHODS_VIEW))],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
) -> PaymentMethodResponse:
    """Get a payment method by ID."""
    result = await service.get_payment_method(payment_method_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )
    return result


@router.get("/{payment_method_id}/usage", response_model=PaymentMethodUsageResponse)
async def get_payment_method_usage(
    payment_method_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PAYMENT_METHODS_VIEW))],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
) -> PaymentMethodUsageResponse:
    """Get providers using a specific payment method."""
    usage = await service.get_payment_method_usage(payment_method_id)
    if usage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )
    return usage


@router.put("/{payment_method_id}", response_model=PaymentMethodResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_payment_method(
    request: Request,
    payment_method_id: UUID,
    data: PaymentMethodUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PAYMENT_METHODS_EDIT))],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
) -> PaymentMethodResponse:
    """Update a payment method. Requires payment_methods.edit permission."""
    try:
        return await service.update_payment_method(
            payment_method_id=payment_method_id,
            data=data,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )


@router.delete("/{payment_method_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_payment_method(
    request: Request,
    payment_method_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PAYMENT_METHODS_DELETE))],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    force: bool = False,
) -> None:
    """Delete a payment method.

    Requires payment_methods.delete permission.
    Returns 409 Conflict if the payment method is in use by providers.
    Use force=true to delete anyway (will unlink from providers).
    """
    try:
        await service.delete_payment_method(
            payment_method_id=payment_method_id,
            user=current_user,
            request=request,
            force=force,
        )
    except ValueError as e:
        error_msg = str(e)
        if "used by" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )
