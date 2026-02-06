"""Provider repository."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.provider import ProviderORM
from licence_api.repositories.base import BaseRepository


class ProviderRepository(BaseRepository[ProviderORM]):
    """Repository for provider operations."""

    model = ProviderORM

    async def get_by_name(self, name: str) -> ProviderORM | None:
        """Get provider by name.

        Args:
            name: Provider name

        Returns:
            ProviderORM or None if not found
        """
        result = await self.session.execute(
            select(ProviderORM).where(ProviderORM.name == name)
        )
        return result.scalar_one_or_none()

    async def get_enabled(self) -> list[ProviderORM]:
        """Get all enabled providers.

        Returns:
            List of enabled providers
        """
        result = await self.session.execute(
            select(ProviderORM).where(ProviderORM.enabled == True)
        )
        return list(result.scalars().all())

    async def get_all_with_license_counts(self) -> list[tuple[ProviderORM, int]]:
        """Get all providers with their license counts.

        Returns:
            List of (provider, license_count) tuples
        """
        from sqlalchemy.orm import noload
        from licence_api.models.orm.license import LicenseORM

        result = await self.session.execute(
            select(ProviderORM, func.count(LicenseORM.id))
            .outerjoin(LicenseORM, ProviderORM.id == LicenseORM.provider_id)
            .options(noload(ProviderORM.payment_method))  # Prevent joined load that breaks GROUP BY
            .group_by(ProviderORM.id)
            .order_by(ProviderORM.display_name)
        )
        return list(result.all())

    async def update_sync_status(
        self,
        id: UUID,
        status: str,
        sync_time: datetime | None = None,
    ) -> ProviderORM | None:
        """Update provider sync status.

        Args:
            id: Provider UUID
            status: Sync status
            sync_time: Sync timestamp (defaults to now)

        Returns:
            Updated provider or None if not found
        """
        provider = await self.get_by_id(id)
        if provider is None:
            return None

        provider.last_sync_status = status
        provider.last_sync_at = sync_time or datetime.now()
        await self.session.flush()
        await self.session.refresh(provider)
        return provider

    async def exists_any(self) -> bool:
        """Check if any providers exist.

        Returns:
            True if at least one provider exists
        """
        result = await self.session.execute(
            select(func.count()).select_from(ProviderORM).limit(1)
        )
        return result.scalar_one() > 0

    async def count_by_payment_method(self, payment_method_id: UUID) -> int:
        """Count providers using a specific payment method.

        Args:
            payment_method_id: Payment method UUID

        Returns:
            Number of providers using this payment method
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(ProviderORM)
            .where(ProviderORM.payment_method_id == payment_method_id)
        )
        return result.scalar_one()

    async def get_by_payment_method(self, payment_method_id: UUID) -> list[ProviderORM]:
        """Get providers using a specific payment method.

        Args:
            payment_method_id: Payment method UUID

        Returns:
            List of providers using this payment method
        """
        result = await self.session.execute(
            select(ProviderORM)
            .where(ProviderORM.payment_method_id == payment_method_id)
            .order_by(ProviderORM.display_name)
        )
        return list(result.scalars().all())
