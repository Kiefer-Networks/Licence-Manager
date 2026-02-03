"""Payment method DTOs."""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreditCardDetails(BaseModel):
    """Credit card details."""

    holder: str = Field(min_length=1, max_length=255)
    last_four: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    expiry_month: int = Field(ge=1, le=12)
    expiry_year: int = Field(ge=2000, le=2100)


class BankAccountDetails(BaseModel):
    """Bank account details."""

    bank_name: str = Field(min_length=1, max_length=255)
    iban_last_four: str | None = Field(default=None, min_length=4, max_length=4, pattern=r"^\d{4}$")
    bic: str | None = Field(default=None, min_length=8, max_length=11, pattern=r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")


class PaymentMethodCreate(BaseModel):
    """Create payment method request."""

    name: str = Field(max_length=255)
    type: str = Field(max_length=50)  # credit_card, bank_account, stripe, paypal, invoice, other
    details: dict[str, Any] = Field(default_factory=dict, max_length=50)
    is_default: bool = False
    notes: str | None = Field(default=None, max_length=2000)


class PaymentMethodUpdate(BaseModel):
    """Update payment method request."""

    name: str | None = Field(default=None, max_length=255)
    details: dict[str, Any] | None = Field(default=None, max_length=50)
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
