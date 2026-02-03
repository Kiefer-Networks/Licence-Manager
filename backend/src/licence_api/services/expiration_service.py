"""Expiration service for tracking and updating expired licenses.

Architecture Note (MVC-07):
    This service handles automated expiration detection and status updates across
    multiple entity types. While it uses repositories for standard operations, some
    methods use direct SQLAlchemy queries because:
    1. Expiration checks require complex date-based filtering with multiple conditions
    2. Batch status updates need to modify multiple records efficiently
    3. Queries join licenses with providers and employees for notification context
    4. Performance-critical scheduled task that runs periodically
    5. Read operations for analytics don't require repository abstraction

    The service combines repository usage (where appropriate) with direct queries
    (for complex analytics) following the patterns established in report_service.py.
"""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_

from licence_api.models.domain.license import LicenseStatus
from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.license_package import LicensePackageORM, PackageStatus
from licence_api.models.orm.organization_license import OrganizationLicenseORM, OrgLicenseStatus
from licence_api.models.orm.employee import EmployeeORM
from licence_api.models.orm.provider import ProviderORM
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.license_package_repository import LicensePackageRepository
from licence_api.repositories.organization_license_repository import OrganizationLicenseRepository


class ExpirationService:
    """Service for tracking license expiration."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.license_repo = LicenseRepository(session)
        self.package_repo = LicensePackageRepository(session)
        self.org_license_repo = OrganizationLicenseRepository(session)

    async def check_and_update_expired_licenses(self) -> dict:
        """Check for expired licenses and update their status.

        Updates:
        - Licenses with expires_at in the past -> status = EXPIRED
        - Licenses with cancellation_effective_date in the past -> status = CANCELLED
        - Packages with contract_end in the past -> status = expired
        - Packages with cancellation_effective_date in the past -> status = cancelled
        - Org licenses similarly

        Returns:
            Dict with counts of updated items
        """
        today = date.today()
        counts = {
            "licenses_expired": 0,
            "licenses_cancelled": 0,
            "packages_expired": 0,
            "packages_cancelled": 0,
            "org_licenses_expired": 0,
            "org_licenses_cancelled": 0,
        }

        # Update expired licenses using repository
        expired_licenses = await self.license_repo.get_expired_needing_update(
            today=today,
            excluded_statuses=[LicenseStatus.EXPIRED, LicenseStatus.CANCELLED],
        )
        for license_orm in expired_licenses:
            license_orm.status = LicenseStatus.EXPIRED
            counts["licenses_expired"] += 1

        # Update cancelled licenses using repository
        cancelled_licenses = await self.license_repo.get_cancelled_needing_update(
            today=today,
            excluded_status=LicenseStatus.CANCELLED,
        )
        for license_orm in cancelled_licenses:
            license_orm.status = LicenseStatus.CANCELLED
            counts["licenses_cancelled"] += 1

        # Update expired packages using repository
        expired_packages = await self.package_repo.get_expired_needing_update(
            today=today,
            excluded_statuses=[PackageStatus.EXPIRED, PackageStatus.CANCELLED],
        )
        for package in expired_packages:
            package.status = PackageStatus.EXPIRED
            counts["packages_expired"] += 1

        # Update cancelled packages using repository
        cancelled_packages = await self.package_repo.get_cancelled_needing_update(
            today=today,
            excluded_status=PackageStatus.CANCELLED,
        )
        for package in cancelled_packages:
            package.status = PackageStatus.CANCELLED
            counts["packages_cancelled"] += 1

        # Update expired org licenses using repository
        expired_org_licenses = await self.org_license_repo.get_expired_needing_update(
            today=today,
            excluded_statuses=[OrgLicenseStatus.EXPIRED, OrgLicenseStatus.CANCELLED],
        )
        for org_lic in expired_org_licenses:
            org_lic.status = OrgLicenseStatus.EXPIRED
            counts["org_licenses_expired"] += 1

        # Update cancelled org licenses using repository
        cancelled_org_licenses = await self.org_license_repo.get_cancelled_needing_update(
            today=today,
            excluded_status=OrgLicenseStatus.CANCELLED,
        )
        for org_lic in cancelled_org_licenses:
            org_lic.status = OrgLicenseStatus.CANCELLED
            counts["org_licenses_cancelled"] += 1

        await self.session.flush()
        return counts

    async def get_expiring_licenses(
        self,
        days_ahead: int = 90,
    ) -> list[tuple[LicenseORM, ProviderORM, EmployeeORM | None]]:
        """Get licenses expiring within specified days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of tuples (license, provider, employee)
        """
        cutoff_date = date.today() + timedelta(days=days_ahead)

        result = await self.session.execute(
            select(LicenseORM, ProviderORM, EmployeeORM)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
            .outerjoin(EmployeeORM, LicenseORM.employee_id == EmployeeORM.id)
            .where(
                and_(
                    LicenseORM.expires_at.isnot(None),
                    LicenseORM.expires_at >= date.today(),
                    LicenseORM.expires_at <= cutoff_date,
                    LicenseORM.status.notin_([LicenseStatus.EXPIRED, LicenseStatus.CANCELLED]),
                )
            )
            .order_by(LicenseORM.expires_at)
        )
        return list(result.all())

    async def get_expiring_packages(
        self,
        days_ahead: int = 90,
    ) -> list[LicensePackageORM]:
        """Get packages with contracts expiring within specified days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of LicensePackageORM
        """
        cutoff_date = date.today() + timedelta(days=days_ahead)

        result = await self.session.execute(
            select(LicensePackageORM)
            .options(selectinload(LicensePackageORM.provider))
            .where(
                and_(
                    LicensePackageORM.contract_end.isnot(None),
                    LicensePackageORM.contract_end >= date.today(),
                    LicensePackageORM.contract_end <= cutoff_date,
                    LicensePackageORM.status.notin_([PackageStatus.EXPIRED, PackageStatus.CANCELLED]),
                )
            )
            .order_by(LicensePackageORM.contract_end)
        )
        return list(result.scalars().all())

    async def get_licenses_needing_reorder(
        self,
    ) -> list[tuple[LicenseORM, ProviderORM, EmployeeORM | None]]:
        """Get licenses marked as needing reorder.

        Returns:
            List of tuples (license, provider, employee)
        """
        result = await self.session.execute(
            select(LicenseORM, ProviderORM, EmployeeORM)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
            .outerjoin(EmployeeORM, LicenseORM.employee_id == EmployeeORM.id)
            .where(LicenseORM.needs_reorder == True)
            .order_by(LicenseORM.expires_at.nulls_last())
        )
        return list(result.all())

    async def get_cancelled_licenses(
        self,
    ) -> list[tuple[LicenseORM, ProviderORM, EmployeeORM | None]]:
        """Get all cancelled licenses (with cancellation info).

        Returns:
            List of tuples (license, provider, employee)
        """
        result = await self.session.execute(
            select(LicenseORM, ProviderORM, EmployeeORM)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
            .outerjoin(EmployeeORM, LicenseORM.employee_id == EmployeeORM.id)
            .where(LicenseORM.cancelled_at.isnot(None))
            .order_by(LicenseORM.cancellation_effective_date)
        )
        return list(result.all())

    async def get_cancelled_packages(
        self,
    ) -> list[LicensePackageORM]:
        """Get all cancelled packages.

        Returns:
            List of LicensePackageORM
        """
        result = await self.session.execute(
            select(LicensePackageORM)
            .options(selectinload(LicensePackageORM.provider))
            .where(LicensePackageORM.cancelled_at.isnot(None))
            .order_by(LicensePackageORM.cancellation_effective_date)
        )
        return list(result.scalars().all())

    async def get_expired_licenses(
        self,
    ) -> list[tuple[LicenseORM, ProviderORM, EmployeeORM | None]]:
        """Get all expired licenses.

        Returns:
            List of tuples (license, provider, employee)
        """
        result = await self.session.execute(
            select(LicenseORM, ProviderORM, EmployeeORM)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
            .outerjoin(EmployeeORM, LicenseORM.employee_id == EmployeeORM.id)
            .where(LicenseORM.status == LicenseStatus.EXPIRED)
            .order_by(LicenseORM.expires_at)
        )
        return list(result.all())
