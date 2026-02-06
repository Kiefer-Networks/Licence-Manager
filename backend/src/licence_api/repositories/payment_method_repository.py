"""Payment method repository."""

from datetime import date
from uuid import UUID

from sqlalchemy import select, update

from licence_api.models.orm.payment_method import PaymentMethodORM
from licence_api.repositories.base import BaseRepository


class PaymentMethodRepository(BaseRepository[PaymentMethodORM]):
    """Repository for payment method operations."""

    model = PaymentMethodORM

    async def get_all(self) -> list[PaymentMethodORM]:
        """Get all payment methods ordered by name."""
        result = await self.session.execute(
            select(PaymentMethodORM).order_by(PaymentMethodORM.name)
        )
        return list(result.scalars().all())

    async def get_default(self) -> PaymentMethodORM | None:
        """Get the default payment method."""
        result = await self.session.execute(
            select(PaymentMethodORM).where(PaymentMethodORM.is_default == True)
        )
        return result.scalar_one_or_none()

    async def set_default(self, payment_method_id: UUID) -> None:
        """Set a payment method as default (and unset others)."""
        # Unset all defaults
        await self.session.execute(update(PaymentMethodORM).values(is_default=False))
        # Set the new default
        await self.session.execute(
            update(PaymentMethodORM)
            .where(PaymentMethodORM.id == payment_method_id)
            .values(is_default=True)
        )
        await self.session.flush()

    async def get_expiring_credit_cards(self, within_days: int = 30) -> list[PaymentMethodORM]:
        """Get credit cards expiring within the specified days."""
        result = await self.session.execute(
            select(PaymentMethodORM).where(PaymentMethodORM.type == "credit_card")
        )
        cards = list(result.scalars().all())

        today = date.today()
        expiring = []

        for card in cards:
            details = card.details or {}
            expiry_month = details.get("expiry_month")
            expiry_year = details.get("expiry_year")

            if expiry_month and expiry_year:
                try:
                    # Last day of expiry month
                    if expiry_month == 12:
                        expiry_date = date(int(expiry_year) + 1, 1, 1)
                    else:
                        expiry_date = date(int(expiry_year), int(expiry_month) + 1, 1)

                    days_until_expiry = (expiry_date - today).days
                    if days_until_expiry <= within_days:
                        expiring.append(card)
                except (ValueError, TypeError):
                    pass

        return expiring
