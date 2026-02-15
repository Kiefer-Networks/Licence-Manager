"""Expiration service for tracking and updating expired licenses.

Architecture Note (MVC-07):
    This service handles automated expiration detection and status updates across
    multiple entity types. It delegates all database queries to the appropriate
    repositories (LicenseRepository, LicensePackageRepository,
    OrganizationLicenseRepository) and keeps only transaction management
    (commit/flush) and business logic in the service layer.
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.license import LicenseStatus
from licence_api.models.orm.employee import EmployeeORM
from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.license_package import LicensePackageORM, PackageStatus
from licence_api.models.orm.organization_license import OrganizationLicenseORM, OrgLicenseStatus
from licence_api.models.orm.provider import ProviderORM
from licence_api.repositories.license_package_repository import LicensePackageRepository
from licence_api.repositories.license_repository import LicenseRepository
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
        return await self.license_repo.get_expiring_with_details(days_ahead=days_ahead)

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
        return await self.package_repo.get_expiring_with_provider(days_ahead=days_ahead)

    async def get_licenses_needing_reorder(
        self,
    ) -> list[tuple[LicenseORM, ProviderORM, EmployeeORM | None]]:
        """Get licenses marked as needing reorder.

        Returns:
            List of tuples (license, provider, employee)
        """
        return await self.license_repo.get_needing_reorder_with_details()

    async def get_cancelled_licenses(
        self,
    ) -> list[tuple[LicenseORM, ProviderORM, EmployeeORM | None]]:
        """Get all cancelled licenses (with cancellation info).

        Returns:
            List of tuples (license, provider, employee)
        """
        return await self.license_repo.get_cancelled_with_details()

    async def get_cancelled_packages(
        self,
    ) -> list[LicensePackageORM]:
        """Get all cancelled packages.

        Returns:
            List of LicensePackageORM
        """
        return await self.package_repo.get_cancelled_with_provider()

    async def get_expiring_org_licenses(
        self,
        days_ahead: int = 90,
    ) -> list[OrganizationLicenseORM]:
        """Get organization licenses expiring within specified days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of OrganizationLicenseORM
        """
        return await self.org_license_repo.get_expiring_with_provider(days_ahead=days_ahead)

    async def get_expired_licenses(
        self,
    ) -> list[tuple[LicenseORM, ProviderORM, EmployeeORM | None]]:
        """Get all expired licenses.

        Returns:
            List of tuples (license, provider, employee)
        """
        return await self.license_repo.get_expired_with_details()
