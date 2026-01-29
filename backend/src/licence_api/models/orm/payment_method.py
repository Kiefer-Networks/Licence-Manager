"""Payment method ORM model."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class PaymentMethodORM(Base, UUIDMixin, TimestampMixin):
    """Payment method database model."""

    __tablename__ = "payment_methods"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Type: credit_card, bank_account, stripe, paypal, invoice, other
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Credit card: holder, last_four, expiry_month, expiry_year
    # Bank: bank_name, iban_last_four, bic
    # Stripe: customer_id
    # Invoice: contact_email, payment_terms
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
