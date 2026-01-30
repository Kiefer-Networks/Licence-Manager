"""Organization license repository."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.organization_license import OrganizationLicenseORM
from licence_api.repositories.base import BaseRepository


class OrganizationLicenseRepository(BaseRepository[OrganizationLicenseORM]):
    """Repository for organization license operations."""

    model = OrganizationLicenseORM

    async def get_by_provider(self, provider_id: UUID) -> list[OrganizationLicenseORM]:
        """Get all organization licenses for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            List of organization licenses
        """
        result = await self.session.execute(
            select(OrganizationLicenseORM)
            .where(OrganizationLicenseORM.provider_id == provider_id)
            .order_by(OrganizationLicenseORM.name)
        )
        return list(result.scalars().all())

    async def get_total_monthly_cost(self, provider_id: UUID) -> Decimal:
        """Get total monthly cost of organization licenses for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            Total monthly cost
        """
        result = await self.session.execute(
            select(func.coalesce(func.sum(OrganizationLicenseORM.monthly_cost), 0))
            .where(OrganizationLicenseORM.provider_id == provider_id)
        )
        return Decimal(str(result.scalar_one()))

    async def get_all_total_monthly_cost(self) -> Decimal:
        """Get total monthly cost of all organization licenses.

        Returns:
            Total monthly cost across all providers
        """
        result = await self.session.execute(
            select(func.coalesce(func.sum(OrganizationLicenseORM.monthly_cost), 0))
        )
        return Decimal(str(result.scalar_one()))
