"""Organization license repository."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from licence_api.models.orm.organization_license import OrganizationLicenseORM
from licence_api.repositories.base import BaseRepository


class OrganizationLicenseRepository(BaseRepository[OrganizationLicenseORM]):
    """Repository for organization license operations."""

    model = OrganizationLicenseORM

    async def get_by_provider_and_id(
        self, provider_id: UUID, license_id: UUID
    ) -> OrganizationLicenseORM | None:
        """Get an organization license by provider and ID.

        Args:
            provider_id: Provider UUID
            license_id: License UUID

        Returns:
            OrganizationLicenseORM or None if not found or wrong provider
        """
        result = await self.session.execute(
            select(OrganizationLicenseORM)
            .where(OrganizationLicenseORM.id == license_id)
            .where(OrganizationLicenseORM.provider_id == provider_id)
        )
        return result.scalar_one_or_none()

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
            select(func.coalesce(func.sum(OrganizationLicenseORM.monthly_cost), 0)).where(
                OrganizationLicenseORM.provider_id == provider_id
            )
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

    async def create_organization_license(
        self,
        provider_id: UUID,
        name: str,
        license_type: str | None = None,
        quantity: int | None = None,
        unit: str | None = None,
        monthly_cost: Decimal | None = None,
        currency: str = "EUR",
        billing_cycle: str | None = None,
        renewal_date: date | None = None,
        notes: str | None = None,
    ) -> OrganizationLicenseORM:
        """Create a new organization license.

        Args:
            provider_id: Provider UUID
            name: License name
            license_type: Type of license
            quantity: Number of licenses
            unit: Unit of measurement
            monthly_cost: Monthly cost
            currency: Currency code
            billing_cycle: Billing cycle
            renewal_date: Renewal date
            notes: Additional notes

        Returns:
            Created OrganizationLicenseORM
        """
        license_orm = OrganizationLicenseORM(
            provider_id=provider_id,
            name=name,
            license_type=license_type,
            quantity=quantity,
            unit=unit,
            monthly_cost=monthly_cost,
            currency=currency,
            billing_cycle=billing_cycle,
            renewal_date=renewal_date,
            notes=notes,
        )
        self.session.add(license_orm)
        await self.session.flush()
        await self.session.refresh(license_orm)
        return license_orm

    async def update_organization_license(
        self,
        license_orm: OrganizationLicenseORM,
        **kwargs,
    ) -> OrganizationLicenseORM:
        """Update an organization license.

        Args:
            license_orm: License to update
            **kwargs: Fields to update

        Returns:
            Updated OrganizationLicenseORM
        """
        for key, value in kwargs.items():
            if hasattr(license_orm, key):
                setattr(license_orm, key, value)
        await self.session.flush()
        await self.session.refresh(license_orm)
        return license_orm

    async def delete_organization_license(self, license_orm: OrganizationLicenseORM) -> None:
        """Delete an organization license.

        Args:
            license_orm: License to delete
        """
        await self.session.delete(license_orm)
        await self.session.flush()

    # =========================================================================
    # Expiration methods (MVC-02 fix)
    # =========================================================================

    async def get_expired_needing_update(
        self,
        today: date,
        excluded_statuses: list[str],
    ) -> list[OrganizationLicenseORM]:
        """Get org licenses that have expired but status not yet updated.

        Args:
            today: Current date
            excluded_statuses: Statuses to exclude

        Returns:
            List of org licenses needing status update
        """
        result = await self.session.execute(
            select(OrganizationLicenseORM).where(
                and_(
                    OrganizationLicenseORM.expires_at.isnot(None),
                    OrganizationLicenseORM.expires_at < today,
                    OrganizationLicenseORM.status.notin_(excluded_statuses),
                )
            )
        )
        return list(result.scalars().all())

    async def get_cancelled_needing_update(
        self,
        today: date,
        excluded_status: str,
    ) -> list[OrganizationLicenseORM]:
        """Get org licenses with passed cancellation date but status not yet updated.

        Args:
            today: Current date
            excluded_status: Status to exclude

        Returns:
            List of org licenses needing status update
        """
        result = await self.session.execute(
            select(OrganizationLicenseORM).where(
                and_(
                    OrganizationLicenseORM.cancellation_effective_date.isnot(None),
                    OrganizationLicenseORM.cancellation_effective_date <= today,
                    OrganizationLicenseORM.status != excluded_status,
                )
            )
        )
        return list(result.scalars().all())
