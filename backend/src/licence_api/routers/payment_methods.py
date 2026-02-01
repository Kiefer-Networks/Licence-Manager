"""Payment methods router."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.payment_method import (
    PaymentMethodCreate,
    PaymentMethodListResponse,
    PaymentMethodResponse,
    PaymentMethodUpdate,
)
from licence_api.security.auth import get_current_user, require_admin
from licence_api.services.payment_method_service import PaymentMethodService

router = APIRouter()


def get_payment_method_service(
    db: AsyncSession = Depends(get_db),
) -> PaymentMethodService:
    """Get PaymentMethodService instance."""
    return PaymentMethodService(db)


@router.get("", response_model=PaymentMethodListResponse)
async def list_payment_methods(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
) -> PaymentMethodListResponse:
    """List all payment methods."""
    return await service.list_payment_methods()


@router.post("", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    http_request: Request,
    data: PaymentMethodCreate,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
) -> PaymentMethodResponse:
    """Create a new payment method. Admin only."""
    try:
        return await service.create_payment_method(
            data=data,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment method data",
        )


@router.get("/{payment_method_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    payment_method_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
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


@router.put("/{payment_method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    http_request: Request,
    payment_method_id: UUID,
    data: PaymentMethodUpdate,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
) -> PaymentMethodResponse:
    """Update a payment method. Admin only."""
    try:
        return await service.update_payment_method(
            payment_method_id=payment_method_id,
            data=data,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )


@router.delete("/{payment_method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    http_request: Request,
    payment_method_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    service: Annotated[PaymentMethodService, Depends(get_payment_method_service)],
) -> None:
    """Delete a payment method. Admin only."""
    try:
        await service.delete_payment_method(
            payment_method_id=payment_method_id,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )
