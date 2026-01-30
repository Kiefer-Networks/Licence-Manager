"""License package repository."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.license_package import LicensePackageORM
from licence_api.models.orm.license import LicenseORM
from licence_api.repositories.base import BaseRepository


class LicensePackageRepository(BaseRepository[LicensePackageORM]):
    """Repository for license package operations."""

    model = LicensePackageORM

    async def get_by_provider(self, provider_id: UUID) -> list[LicensePackageORM]:
        """Get all license packages for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            List of license packages
        """
        result = await self.session.execute(
            select(LicensePackageORM)
            .where(LicensePackageORM.provider_id == provider_id)
            .order_by(LicensePackageORM.license_type)
        )
        return list(result.scalars().all())

    async def get_by_provider_and_type(
        self, provider_id: UUID, license_type: str
    ) -> LicensePackageORM | None:
        """Get a license package by provider and type.

        Args:
            provider_id: Provider UUID
            license_type: License type string

        Returns:
            License package or None
        """
        result = await self.session.execute(
            select(LicensePackageORM).where(
                LicensePackageORM.provider_id == provider_id,
                LicensePackageORM.license_type == license_type,
            )
        )
        return result.scalar_one_or_none()

    async def get_assigned_seats_count(
        self, provider_id: UUID, license_type: str
    ) -> int:
        """Count assigned seats for a license type.

        Args:
            provider_id: Provider UUID
            license_type: License type string

        Returns:
            Number of assigned licenses (with employee_id)
        """
        result = await self.session.execute(
            select(func.count(LicenseORM.id)).where(
                LicenseORM.provider_id == provider_id,
                LicenseORM.license_type == license_type,
                LicenseORM.employee_id.isnot(None),
                LicenseORM.is_service_account == False,  # noqa: E712
            )
        )
        return result.scalar_one()

    async def get_all_assigned_seats_counts(
        self, provider_id: UUID
    ) -> dict[str, int]:
        """Get assigned seat counts for all license types of a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            Dict mapping license_type to assigned count
        """
        result = await self.session.execute(
            select(
                LicenseORM.license_type,
                func.count(LicenseORM.id),
            )
            .where(
                LicenseORM.provider_id == provider_id,
                LicenseORM.employee_id.isnot(None),
                LicenseORM.is_service_account == False,  # noqa: E712
            )
            .group_by(LicenseORM.license_type)
        )
        return {row[0]: row[1] for row in result.all() if row[0]}
