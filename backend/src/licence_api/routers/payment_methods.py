"""Payment methods router."""

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.repositories.payment_method_repository import PaymentMethodRepository
from licence_api.security.auth import get_current_user, require_admin
from licence_api.services.audit_service import AuditService, AuditAction, ResourceType

router = APIRouter()


class CreditCardDetails(BaseModel):
    """Credit card details."""
    holder: str
    last_four: str
    expiry_month: int
    expiry_year: int


class BankAccountDetails(BaseModel):
    """Bank account details."""
    bank_name: str
    iban_last_four: str | None = None
    bic: str | None = None


class PaymentMethodCreate(BaseModel):
    """Create payment method request."""
    name: str
    type: str  # credit_card, bank_account, stripe, paypal, invoice, other
    details: dict[str, Any] = {}
    is_default: bool = False
    notes: str | None = None


class PaymentMethodUpdate(BaseModel):
    """Update payment method request."""
    name: str | None = None
    details: dict[str, Any] | None = None
    is_default: bool | None = None
    notes: str | None = None


class PaymentMethodResponse(BaseModel):
    """Payment method response."""
    id: UUID
    name: str
    type: str
    details: dict[str, Any]
    is_default: bool
    notes: str | None
    is_expiring: bool = False
    days_until_expiry: int | None = None

    class Config:
        from_attributes = True


class PaymentMethodListResponse(BaseModel):
    """Payment method list response."""
    items: list[PaymentMethodResponse]
    total: int


def calculate_expiry_info(payment_method) -> tuple[bool, int | None]:
    """Calculate expiry info for credit cards."""
    if payment_method.type != "credit_card":
        return False, None

    details = payment_method.details or {}
    expiry_month = details.get("expiry_month")
    expiry_year = details.get("expiry_year")

    if not expiry_month or not expiry_year:
        return False, None

    today = date.today()

    try:
        # Last day of expiry month
        if int(expiry_month) == 12:
            expiry_date = date(int(expiry_year) + 1, 1, 1)
        else:
            expiry_date = date(int(expiry_year), int(expiry_month) + 1, 1)

        days_until = (expiry_date - today).days
        return days_until <= 60, days_until  # Warn 60 days before
    except (ValueError, TypeError):
        return False, None


@router.get("", response_model=PaymentMethodListResponse)
async def list_payment_methods(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentMethodListResponse:
    """List all payment methods."""
    repo = PaymentMethodRepository(db)
    methods = await repo.get_all()

    items = []
    for m in methods:
        is_expiring, days_until = calculate_expiry_info(m)
        items.append(
            PaymentMethodResponse(
                id=m.id,
                name=m.name,
                type=m.type,
                details=m.details,
                is_default=m.is_default,
                notes=m.notes,
                is_expiring=is_expiring,
                days_until_expiry=days_until,
            )
        )

    return PaymentMethodListResponse(items=items, total=len(items))


@router.post("", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    http_request: Request,
    request: PaymentMethodCreate,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentMethodResponse:
    """Create a new payment method. Admin only."""
    repo = PaymentMethodRepository(db)

    # Validate type
    valid_types = ["credit_card", "bank_account", "stripe", "paypal", "invoice", "other"]
    if request.type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid type. Must be one of: {', '.join(valid_types)}",
        )

    method = await repo.create(
        name=request.name,
        type=request.type,
        details=request.details,
        is_default=request.is_default,
        notes=request.notes,
    )

    if request.is_default:
        await repo.set_default(method.id)

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.PAYMENT_METHOD_CREATE,
        resource_type=ResourceType.PAYMENT_METHOD,
        resource_id=method.id,
        user=current_user,
        request=http_request,
        details={"name": request.name, "type": request.type, "is_default": request.is_default},
    )

    await db.commit()
    await db.refresh(method)

    is_expiring, days_until = calculate_expiry_info(method)
    return PaymentMethodResponse(
        id=method.id,
        name=method.name,
        type=method.type,
        details=method.details,
        is_default=method.is_default,
        notes=method.notes,
        is_expiring=is_expiring,
        days_until_expiry=days_until,
    )


@router.get("/{payment_method_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    payment_method_id: UUID,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentMethodResponse:
    """Get a payment method by ID."""
    repo = PaymentMethodRepository(db)
    method = await repo.get_by_id(payment_method_id)

    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )

    is_expiring, days_until = calculate_expiry_info(method)
    return PaymentMethodResponse(
        id=method.id,
        name=method.name,
        type=method.type,
        details=method.details,
        is_default=method.is_default,
        notes=method.notes,
        is_expiring=is_expiring,
        days_until_expiry=days_until,
    )


@router.put("/{payment_method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    http_request: Request,
    payment_method_id: UUID,
    request: PaymentMethodUpdate,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentMethodResponse:
    """Update a payment method. Admin only."""
    repo = PaymentMethodRepository(db)
    method = await repo.get_by_id(payment_method_id)

    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )

    update_data = {}
    changes = {}
    if request.name is not None:
        update_data["name"] = request.name
        changes["name"] = {"old": method.name, "new": request.name}
    if request.details is not None:
        update_data["details"] = request.details
        changes["details_updated"] = True
    if request.notes is not None:
        update_data["notes"] = request.notes
        changes["notes_updated"] = True

    if update_data:
        method = await repo.update(payment_method_id, **update_data)

    if request.is_default:
        await repo.set_default(payment_method_id)
        changes["is_default"] = {"old": False, "new": True}

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.PAYMENT_METHOD_UPDATE,
        resource_type=ResourceType.PAYMENT_METHOD,
        resource_id=payment_method_id,
        user=current_user,
        request=http_request,
        details={"changes": changes},
    )

    await db.commit()
    await db.refresh(method)

    is_expiring, days_until = calculate_expiry_info(method)
    return PaymentMethodResponse(
        id=method.id,
        name=method.name,
        type=method.type,
        details=method.details,
        is_default=method.is_default,
        notes=method.notes,
        is_expiring=is_expiring,
        days_until_expiry=days_until,
    )


@router.delete("/{payment_method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    http_request: Request,
    payment_method_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a payment method. Admin only."""
    repo = PaymentMethodRepository(db)

    # Get method info for audit before deletion
    method = await repo.get_by_id(payment_method_id)
    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )

    method_name = method.name
    method_type = method.type

    deleted = await repo.delete(payment_method_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.PAYMENT_METHOD_DELETE,
        resource_type=ResourceType.PAYMENT_METHOD,
        resource_id=payment_method_id,
        user=current_user,
        request=http_request,
        details={"name": method_name, "type": method_type},
    )

    await db.commit()
