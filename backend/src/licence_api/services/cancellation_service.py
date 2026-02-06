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

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from licence_api.models.domain.license import LicenseStatus
from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.license_package import LicensePackageORM, PackageStatus
from licence_api.models.orm.organization_license import OrganizationLicenseORM, OrgLicenseStatus
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.repositories.user_repository import UserRepository
from licence_api.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class CancellationService:
    """Service for managing license cancellations and renewals."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.notification_service = NotificationService(session)
        self.settings_repo = SettingsRepository(session)
        self.user_repo = UserRepository(session)

    async def _get_slack_token(self) -> str | None:
        """Get Slack bot token from settings."""
        slack_config = await self.settings_repo.get("slack_config")
        return slack_config.get("bot_token") if slack_config else None

    async def _get_user_email(self, user_id: UUID) -> str:
        """Get user email by ID."""
        user = await self.user_repo.get_by_id(user_id)
        return user.email if user else "Unknown"

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
            select(LicenseORM)
            .options(selectinload(LicenseORM.provider))
            .where(LicenseORM.id == license_id)
        )
        license_orm = result.scalar_one_or_none()

        if license_orm is None:
            raise ValueError(f"License {license_id} not found")

        license_orm.cancelled_at = datetime.now(UTC)
        license_orm.cancellation_effective_date = effective_date
        license_orm.cancellation_reason = reason
        license_orm.cancelled_by = cancelled_by

        # If effective date is today or in the past, mark as cancelled
        if effective_date <= date.today():
            license_orm.status = LicenseStatus.CANCELLED

        await self.session.commit()
        await self.session.refresh(license_orm)

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                cancelled_by_email = await self._get_user_email(cancelled_by)
                await self.notification_service.notify_license_cancelled(
                    provider_name=license_orm.provider.display_name
                    if license_orm.provider
                    else "Unknown",
                    license_type=license_orm.license_type,
                    user_email=license_orm.external_user_id,
                    cancelled_by=cancelled_by_email,
                    cancellation_reason=reason,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send cancellation notification: {e}")

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

        package.cancelled_at = datetime.now(UTC)
        package.cancellation_effective_date = effective_date
        package.cancellation_reason = reason
        package.cancelled_by = cancelled_by

        # If effective date is today or in the past, mark as cancelled
        if effective_date <= date.today():
            package.status = PackageStatus.CANCELLED

        await self.session.commit()
        await self.session.refresh(package)

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                cancelled_by_email = await self._get_user_email(cancelled_by)
                await self.notification_service.notify_package_cancelled(
                    provider_name=package.provider.display_name if package.provider else "Unknown",
                    package_name=package.license_type or "Unknown",
                    seat_count=package.seats or 0,
                    cancelled_by=cancelled_by_email,
                    cancellation_reason=reason,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send package cancellation notification: {e}")

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

        org_license.cancelled_at = datetime.now(UTC)
        org_license.cancellation_effective_date = effective_date
        org_license.cancellation_reason = reason
        org_license.cancelled_by = cancelled_by

        # If effective date is today or in the past, mark as cancelled
        if effective_date <= date.today():
            org_license.status = OrgLicenseStatus.CANCELLED

        await self.session.commit()
        await self.session.refresh(org_license)

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                cancelled_by_email = await self._get_user_email(cancelled_by)
                await self.notification_service.notify_org_license_cancelled(
                    provider_name=org_license.provider.display_name
                    if org_license.provider
                    else "Unknown",
                    org_license_name=org_license.name,
                    cancelled_by=cancelled_by_email,
                    cancellation_reason=reason,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send org license cancellation notification: {e}")

        return org_license

    async def renew_license(
        self,
        license_id: UUID,
        new_expiration_date: date,
        renewed_by: UUID,
        clear_cancellation: bool = True,
    ) -> LicenseORM:
        """Renew a license by setting a new expiration date.

        Args:
            license_id: License UUID
            new_expiration_date: New expiration date
            renewed_by: Admin user who renewed
            clear_cancellation: Whether to clear cancellation data

        Returns:
            Updated LicenseORM

        Raises:
            ValueError: If license not found
        """
        result = await self.session.execute(
            select(LicenseORM)
            .options(selectinload(LicenseORM.provider))
            .where(LicenseORM.id == license_id)
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

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                renewed_by_email = await self._get_user_email(renewed_by)
                await self.notification_service.notify_license_renewed(
                    provider_name=license_orm.provider.display_name
                    if license_orm.provider
                    else "Unknown",
                    license_type=license_orm.license_type,
                    user_email=license_orm.external_user_id,
                    renewed_by=renewed_by_email,
                    new_expiration_date=new_expiration_date.isoformat()
                    if new_expiration_date
                    else None,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send license renewal notification: {e}")

        return license_orm

    async def renew_package(
        self,
        package_id: UUID,
        new_contract_end: date,
        renewed_by: UUID,
        clear_cancellation: bool = True,
    ) -> LicensePackageORM:
        """Renew a license package by setting a new contract end date.

        Args:
            package_id: Package UUID
            new_contract_end: New contract end date
            renewed_by: Admin user who renewed
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

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                renewed_by_email = await self._get_user_email(renewed_by)
                await self.notification_service.notify_package_renewed(
                    provider_name=package.provider.display_name if package.provider else "Unknown",
                    package_name=package.license_type or "Unknown",
                    seat_count=package.total_seats or 0,
                    renewed_by=renewed_by_email,
                    new_contract_end=new_contract_end.isoformat() if new_contract_end else None,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send package renewal notification: {e}")

        return package

    async def set_license_needs_reorder(
        self,
        license_id: UUID,
        needs_reorder: bool,
        flagged_by: UUID | None = None,
    ) -> LicenseORM:
        """Set the needs_reorder flag for a license.

        Args:
            license_id: License UUID
            needs_reorder: Whether license needs reorder
            flagged_by: Admin user who flagged (optional, for notification)

        Returns:
            Updated LicenseORM

        Raises:
            ValueError: If license not found
        """
        result = await self.session.execute(
            select(LicenseORM)
            .options(selectinload(LicenseORM.provider))
            .where(LicenseORM.id == license_id)
        )
        license_orm = result.scalar_one_or_none()

        if license_orm is None:
            raise ValueError(f"License {license_id} not found")

        license_orm.needs_reorder = needs_reorder

        await self.session.commit()
        await self.session.refresh(license_orm)

        # Send notification when flagging for reorder (fire-and-forget)
        if needs_reorder and flagged_by:
            try:
                slack_token = await self._get_slack_token()
                if slack_token:
                    flagged_by_email = await self._get_user_email(flagged_by)
                    await self.notification_service.notify_license_needs_reorder(
                        provider_name=license_orm.provider.display_name
                        if license_orm.provider
                        else "Unknown",
                        license_type=license_orm.license_type,
                        user_email=license_orm.external_user_id,
                        flagged_by=flagged_by_email,
                        slack_token=slack_token,
                    )
            except Exception as e:
                logger.warning(f"Failed to send license needs reorder notification: {e}")

        return license_orm

    async def set_package_needs_reorder(
        self,
        package_id: UUID,
        needs_reorder: bool,
        flagged_by: UUID | None = None,
    ) -> LicensePackageORM:
        """Set the needs_reorder flag for a package.

        Args:
            package_id: Package UUID
            needs_reorder: Whether package needs reorder
            flagged_by: Admin user who flagged (optional, for notification)

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

        # Send notification when flagging for reorder (fire-and-forget)
        if needs_reorder and flagged_by:
            try:
                slack_token = await self._get_slack_token()
                if slack_token:
                    flagged_by_email = await self._get_user_email(flagged_by)
                    await self.notification_service.notify_package_needs_reorder(
                        provider_name=package.provider.display_name
                        if package.provider
                        else "Unknown",
                        package_name=package.license_type or "Unknown",
                        seat_count=package.total_seats or 0,
                        flagged_by=flagged_by_email,
                        slack_token=slack_token,
                    )
            except Exception as e:
                logger.warning(f"Failed to send package needs reorder notification: {e}")

        return package

    async def renew_org_license(
        self,
        org_license_id: UUID,
        renewed_by: UUID,
        new_renewal_date: date | None = None,
        new_expires_at: date | None = None,
        clear_cancellation: bool = True,
    ) -> OrganizationLicenseORM:
        """Renew an organization license by setting new renewal/expiration dates.

        Args:
            org_license_id: Organization license UUID
            renewed_by: Admin user who renewed
            new_renewal_date: New renewal date (optional)
            new_expires_at: New expiration date (optional)
            clear_cancellation: Whether to clear cancellation data

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

        if new_renewal_date is not None:
            org_license.renewal_date = new_renewal_date
        if new_expires_at is not None:
            org_license.expires_at = new_expires_at
        org_license.needs_reorder = False

        if clear_cancellation:
            org_license.cancelled_at = None
            org_license.cancellation_effective_date = None
            org_license.cancellation_reason = None
            org_license.cancelled_by = None

            # Reset status if it was cancelled or expired
            if org_license.status in (OrgLicenseStatus.CANCELLED, OrgLicenseStatus.EXPIRED):
                org_license.status = OrgLicenseStatus.ACTIVE

        await self.session.commit()
        await self.session.refresh(org_license)

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                renewed_by_email = await self._get_user_email(renewed_by)
                expiry_date = new_expires_at or new_renewal_date
                await self.notification_service.notify_org_license_renewed(
                    provider_name=org_license.provider.display_name
                    if org_license.provider
                    else "Unknown",
                    org_license_name=org_license.name,
                    renewed_by=renewed_by_email,
                    new_expiration_date=expiry_date.isoformat() if expiry_date else None,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send org license renewal notification: {e}")

        return org_license

    async def set_org_license_needs_reorder(
        self,
        org_license_id: UUID,
        needs_reorder: bool,
        flagged_by: UUID | None = None,
    ) -> OrganizationLicenseORM:
        """Set the needs_reorder flag for an organization license.

        Args:
            org_license_id: Organization license UUID
            needs_reorder: Whether org license needs reorder
            flagged_by: Admin user who flagged (optional, for notification)

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

        org_license.needs_reorder = needs_reorder

        await self.session.commit()
        await self.session.refresh(org_license)

        # Send notification when flagging for reorder (fire-and-forget)
        if needs_reorder and flagged_by:
            try:
                slack_token = await self._get_slack_token()
                if slack_token:
                    flagged_by_email = await self._get_user_email(flagged_by)
                    await self.notification_service.notify_org_license_needs_reorder(
                        provider_name=org_license.provider.display_name
                        if org_license.provider
                        else "Unknown",
                        org_license_name=org_license.name,
                        flagged_by=flagged_by_email,
                        slack_token=slack_token,
                    )
            except Exception as e:
                logger.warning(f"Failed to send org license needs reorder notification: {e}")

        return org_license
