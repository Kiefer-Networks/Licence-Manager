"""License package repository."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func, and_

from licence_api.models.orm.license_package import LicensePackageORM, PackageStatus
from licence_api.models.orm.license import LicenseORM
from licence_api.repositories.base import BaseRepository


class LicensePackageRepository(BaseRepository[LicensePackageORM]):
    """Repository for license package operations."""

    model = LicensePackageORM

    async def get_by_provider_and_id(
        self, provider_id: UUID, package_id: UUID
    ) -> LicensePackageORM | None:
        """Get a license package by provider and ID.

        Args:
            provider_id: Provider UUID
            package_id: Package UUID

        Returns:
            LicensePackageORM or None if not found or wrong provider
        """
        result = await self.session.execute(
            select(LicensePackageORM)
            .where(LicensePackageORM.id == package_id)
            .where(LicensePackageORM.provider_id == provider_id)
        )
        return result.scalar_one_or_none()

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

    async def create_package(
        self,
        provider_id: UUID,
        license_type: str,
        display_name: str | None = None,
        total_seats: int = 0,
        cost_per_seat: Decimal | None = None,
        billing_cycle: str | None = None,
        payment_frequency: str | None = None,
        currency: str = "EUR",
        contract_start: date | None = None,
        contract_end: date | None = None,
        auto_renew: bool = False,
        notes: str | None = None,
    ) -> LicensePackageORM:
        """Create a new license package.

        Args:
            provider_id: Provider UUID
            license_type: License type string
            display_name: Display name
            total_seats: Total number of seats
            cost_per_seat: Cost per seat
            billing_cycle: Billing cycle
            payment_frequency: Payment frequency
            currency: Currency code
            contract_start: Contract start date
            contract_end: Contract end date
            auto_renew: Auto renewal flag
            notes: Additional notes

        Returns:
            Created LicensePackageORM
        """
        package = LicensePackageORM(
            provider_id=provider_id,
            license_type=license_type,
            display_name=display_name,
            total_seats=total_seats,
            cost_per_seat=cost_per_seat,
            billing_cycle=billing_cycle,
            payment_frequency=payment_frequency,
            currency=currency,
            contract_start=contract_start,
            contract_end=contract_end,
            auto_renew=auto_renew,
            notes=notes,
        )
        self.session.add(package)
        await self.session.flush()
        await self.session.refresh(package)
        return package

    async def update_package(
        self,
        package: LicensePackageORM,
        **kwargs,
    ) -> LicensePackageORM:
        """Update a license package.

        Args:
            package: Package to update
            **kwargs: Fields to update

        Returns:
            Updated LicensePackageORM
        """
        for key, value in kwargs.items():
            if hasattr(package, key):
                setattr(package, key, value)
        await self.session.flush()
        await self.session.refresh(package)
        return package

    async def delete_package(self, package: LicensePackageORM) -> None:
        """Delete a license package.

        Args:
            package: Package to delete
        """
        await self.session.delete(package)
        await self.session.flush()

    # =========================================================================
    # Expiration methods (MVC-02 fix)
    # =========================================================================

    async def get_expired_needing_update(
        self,
        today: date,
        excluded_statuses: list[str],
    ) -> list[LicensePackageORM]:
        """Get packages that have expired but status not yet updated.

        Args:
            today: Current date
            excluded_statuses: Statuses to exclude

        Returns:
            List of packages needing status update
        """
        result = await self.session.execute(
            select(LicensePackageORM).where(
                and_(
                    LicensePackageORM.contract_end.isnot(None),
                    LicensePackageORM.contract_end < today,
                    LicensePackageORM.status.notin_(excluded_statuses),
                    LicensePackageORM.auto_renew == False,
                )
            )
        )
        return list(result.scalars().all())

    async def get_cancelled_needing_update(
        self,
        today: date,
        excluded_status: str,
    ) -> list[LicensePackageORM]:
        """Get packages with passed cancellation date but status not yet updated.

        Args:
            today: Current date
            excluded_status: Status to exclude

        Returns:
            List of packages needing status update
        """
        result = await self.session.execute(
            select(LicensePackageORM).where(
                and_(
                    LicensePackageORM.cancellation_effective_date.isnot(None),
                    LicensePackageORM.cancellation_effective_date <= today,
                    LicensePackageORM.status != excluded_status,
                )
            )
        )
        return list(result.scalars().all())
