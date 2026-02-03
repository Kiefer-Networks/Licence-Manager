"""Cancellation service for managing license cancellations and renewals.

Architecture Note (MVC-06):
    This service manages the lifecycle state transitions for licenses, packages, and
    organization licenses. It uses direct SQLAlchemy access because:
    1. Cancellation/renewal operations modify multiple related fields atomically
    2. State transitions require immediate consistency (status + dates + metadata)
    3. Operations span multiple entity types (License, Package, OrgLicense) with
       similar but distinct field sets that don't fit a generic repository pattern
    4. Each operation is a single-entity update with business-specific field logic
    5. Transaction commit is done here to ensure atomic state changes

    The service is intentionally thin and focused on state management rather than
    complex queries, keeping the cancellation business logic in one place.
"""

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from licence_api.models.domain.license import LicenseStatus
from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.license_package import LicensePackageORM, PackageStatus
from licence_api.models.orm.organization_license import OrganizationLicenseORM, OrgLicenseStatus


class CancellationService:
    """Service for managing license cancellations and renewals."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session

    async def cancel_license(
        self,
        license_id: UUID,
        effective_date: date,
        reason: str | None,
        cancelled_by: UUID,
    ) -> LicenseORM:
        """Cancel a license.

        Args:
            license_id: License UUID
            effective_date: Date when cancellation becomes effective
            reason: Cancellation reason
            cancelled_by: Admin user who cancelled

        Returns:
            Updated LicenseORM

        Raises:
            ValueError: If license not found
        """
        result = await self.session.execute(
            select(LicenseORM).where(LicenseORM.id == license_id)
        )
        license_orm = result.scalar_one_or_none()

        if license_orm is None:
            raise ValueError(f"License {license_id} not found")

        license_orm.cancelled_at = datetime.now(timezone.utc)
        license_orm.cancellation_effective_date = effective_date
        license_orm.cancellation_reason = reason
        license_orm.cancelled_by = cancelled_by

        # If effective date is today or in the past, mark as cancelled
        if effective_date <= date.today():
            license_orm.status = LicenseStatus.CANCELLED

        await self.session.commit()
        await self.session.refresh(license_orm)
        return license_orm

    async def cancel_package(
        self,
        package_id: UUID,
        effective_date: date,
        reason: str | None,
        cancelled_by: UUID,
    ) -> LicensePackageORM:
        """Cancel a license package.

        Args:
            package_id: Package UUID
            effective_date: Date when cancellation becomes effective
            reason: Cancellation reason
            cancelled_by: Admin user who cancelled

        Returns:
            Updated LicensePackageORM

        Raises:
            ValueError: If package not found
        """
        result = await self.session.execute(
            select(LicensePackageORM)
            .options(selectinload(LicensePackageORM.provider))
            .where(LicensePackageORM.id == package_id)
        )
        package = result.scalar_one_or_none()

        if package is None:
            raise ValueError(f"Package {package_id} not found")

        package.cancelled_at = datetime.now(timezone.utc)
        package.cancellation_effective_date = effective_date
        package.cancellation_reason = reason
        package.cancelled_by = cancelled_by

        # If effective date is today or in the past, mark as cancelled
        if effective_date <= date.today():
            package.status = PackageStatus.CANCELLED

        await self.session.commit()
        await self.session.refresh(package)
        return package

    async def cancel_org_license(
        self,
        org_license_id: UUID,
        effective_date: date,
        reason: str | None,
        cancelled_by: UUID,
    ) -> OrganizationLicenseORM:
        """Cancel an organization license.

        Args:
            org_license_id: Organization license UUID
            effective_date: Date when cancellation becomes effective
            reason: Cancellation reason
            cancelled_by: Admin user who cancelled

        Returns:
            Updated OrganizationLicenseORM

        Raises:
            ValueError: If org license not found
        """
        result = await self.session.execute(
            select(OrganizationLicenseORM)
            .options(selectinload(OrganizationLicenseORM.provider))
            .where(OrganizationLicenseORM.id == org_license_id)
        )
        org_license = result.scalar_one_or_none()

        if org_license is None:
            raise ValueError(f"Organization license {org_license_id} not found")

        org_license.cancelled_at = datetime.now(timezone.utc)
        org_license.cancellation_effective_date = effective_date
        org_license.cancellation_reason = reason
        org_license.cancelled_by = cancelled_by

        # If effective date is today or in the past, mark as cancelled
        if effective_date <= date.today():
            org_license.status = OrgLicenseStatus.CANCELLED

        await self.session.commit()
        await self.session.refresh(org_license)
        return org_license

    async def renew_license(
        self,
        license_id: UUID,
        new_expiration_date: date,
        clear_cancellation: bool = True,
    ) -> LicenseORM:
        """Renew a license by setting a new expiration date.

        Args:
            license_id: License UUID
            new_expiration_date: New expiration date
            clear_cancellation: Whether to clear cancellation data

        Returns:
            Updated LicenseORM

        Raises:
            ValueError: If license not found
        """
        result = await self.session.execute(
            select(LicenseORM).where(LicenseORM.id == license_id)
        )
        license_orm = result.scalar_one_or_none()

        if license_orm is None:
            raise ValueError(f"License {license_id} not found")

        license_orm.expires_at = new_expiration_date
        license_orm.needs_reorder = False

        if clear_cancellation:
            license_orm.cancelled_at = None
            license_orm.cancellation_effective_date = None
            license_orm.cancellation_reason = None
            license_orm.cancelled_by = None

            # Reset status if it was cancelled or expired
            if license_orm.status in (LicenseStatus.CANCELLED, LicenseStatus.EXPIRED):
                license_orm.status = LicenseStatus.ACTIVE

        await self.session.commit()
        await self.session.refresh(license_orm)
        return license_orm

    async def renew_package(
        self,
        package_id: UUID,
        new_contract_end: date,
        clear_cancellation: bool = True,
    ) -> LicensePackageORM:
        """Renew a license package by setting a new contract end date.

        Args:
            package_id: Package UUID
            new_contract_end: New contract end date
            clear_cancellation: Whether to clear cancellation data

        Returns:
            Updated LicensePackageORM

        Raises:
            ValueError: If package not found
        """
        result = await self.session.execute(
            select(LicensePackageORM)
            .options(selectinload(LicensePackageORM.provider))
            .where(LicensePackageORM.id == package_id)
        )
        package = result.scalar_one_or_none()

        if package is None:
            raise ValueError(f"Package {package_id} not found")

        package.contract_end = new_contract_end
        package.needs_reorder = False

        if clear_cancellation:
            package.cancelled_at = None
            package.cancellation_effective_date = None
            package.cancellation_reason = None
            package.cancelled_by = None

            # Reset status if it was cancelled or expired
            if package.status in (PackageStatus.CANCELLED, PackageStatus.EXPIRED):
                package.status = PackageStatus.ACTIVE

        await self.session.commit()
        await self.session.refresh(package)
        return package

    async def set_license_needs_reorder(
        self,
        license_id: UUID,
        needs_reorder: bool,
    ) -> LicenseORM:
        """Set the needs_reorder flag for a license.

        Args:
            license_id: License UUID
            needs_reorder: Whether license needs reorder

        Returns:
            Updated LicenseORM

        Raises:
            ValueError: If license not found
        """
        result = await self.session.execute(
            select(LicenseORM).where(LicenseORM.id == license_id)
        )
        license_orm = result.scalar_one_or_none()

        if license_orm is None:
            raise ValueError(f"License {license_id} not found")

        license_orm.needs_reorder = needs_reorder

        await self.session.commit()
        await self.session.refresh(license_orm)
        return license_orm

    async def set_package_needs_reorder(
        self,
        package_id: UUID,
        needs_reorder: bool,
    ) -> LicensePackageORM:
        """Set the needs_reorder flag for a package.

        Args:
            package_id: Package UUID
            needs_reorder: Whether package needs reorder

        Returns:
            Updated LicensePackageORM

        Raises:
            ValueError: If package not found
        """
        result = await self.session.execute(
            select(LicensePackageORM)
            .options(selectinload(LicensePackageORM.provider))
            .where(LicensePackageORM.id == package_id)
        )
        package = result.scalar_one_or_none()

        if package is None:
            raise ValueError(f"Package {package_id} not found")

        package.needs_reorder = needs_reorder

        await self.session.commit()
        await self.session.refresh(package)
        return package
