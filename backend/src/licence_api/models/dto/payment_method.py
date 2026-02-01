"""Payment method DTOs."""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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

    name: str = Field(max_length=255)
    type: str = Field(max_length=50)  # credit_card, bank_account, stripe, paypal, invoice, other
    details: dict[str, Any] = {}
    is_default: bool = False
    notes: str | None = Field(default=None, max_length=2000)


class PaymentMethodUpdate(BaseModel):
    """Update payment method request."""

    name: str | None = Field(default=None, max_length=255)
    details: dict[str, Any] | None = None
    is_default: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)


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
