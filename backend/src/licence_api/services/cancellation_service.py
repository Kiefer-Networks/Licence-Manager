"""Cancellation service for managing license cancellations and renewals.

Architecture Note (MVC-06):
    This service manages the lifecycle state transitions for licenses, packages, and
    organization licenses. It delegates all database queries to the appropriate
    repositories (LicenseRepository, LicensePackageRepository,
    OrganizationLicenseRepository) and keeps only transaction management
    (commit/flush) and business logic in the service layer.

    Audit logging is handled within this service layer (not in routers) to
    enforce strict MVC separation.
"""

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.domain.license import LicenseStatus
from licence_api.models.dto.cancellation import (
    CancellationResponse,
    NeedsReorderResponse,
    RenewalResponse,
)
from licence_api.models.orm.license_package import PackageStatus
from licence_api.models.orm.organization_license import OrgLicenseStatus
from licence_api.repositories.license_package_repository import LicensePackageRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.organization_license_repository import OrganizationLicenseRepository
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.repositories.user_repository import UserRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
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
        self.license_repo = LicenseRepository(session)
        self.package_repo = LicensePackageRepository(session)
        self.org_license_repo = OrganizationLicenseRepository(session)
        self.audit_service = AuditService(session)

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
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> CancellationResponse:
        """Cancel a license.

        Args:
            license_id: License UUID
            effective_date: Date when cancellation becomes effective
            reason: Cancellation reason
            cancelled_by: Admin user who cancelled
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            CancellationResponse DTO

        Raises:
            ValueError: If license not found
        """
        license_orm = await self.license_repo.get_by_id_with_provider(license_id)

        if license_orm is None:
            raise ValueError(f"License {license_id} not found")

        license_orm.cancelled_at = datetime.now(UTC)
        license_orm.cancellation_effective_date = effective_date
        license_orm.cancellation_reason = reason
        license_orm.cancelled_by = cancelled_by

        # If effective date is today or in the past, mark as cancelled
        if effective_date <= date.today():
            license_orm.status = LicenseStatus.CANCELLED

        # Store notification data before commit to avoid extra SELECT after expire
        provider_name = license_orm.provider.display_name if license_orm.provider else "Unknown"
        license_type = license_orm.license_type
        external_user_id = license_orm.external_user_id

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.LICENSE_CANCEL,
                resource_type=ResourceType.LICENSE,
                resource_id=license_id,
                user=user,
                request=request,
                details={
                    "effective_date": effective_date.isoformat() if effective_date else None,
                    "reason": reason,
                },
            )

        await self.session.commit()

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                cancelled_by_email = await self._get_user_email(cancelled_by)
                await self.notification_service.notify_license_cancelled(
                    provider_name=provider_name,
                    license_type=license_type,
                    user_email=external_user_id,
                    cancelled_by=cancelled_by_email,
                    cancellation_reason=reason,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send cancellation notification: {e}")

        return CancellationResponse(
            id=license_orm.id,
            cancelled_at=license_orm.cancelled_at,
            cancellation_effective_date=license_orm.cancellation_effective_date,
            cancellation_reason=license_orm.cancellation_reason,
            cancelled_by=license_orm.cancelled_by,
        )

    async def cancel_package(
        self,
        package_id: UUID,
        effective_date: date,
        reason: str | None,
        cancelled_by: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> CancellationResponse:
        """Cancel a license package.

        Args:
            package_id: Package UUID
            effective_date: Date when cancellation becomes effective
            reason: Cancellation reason
            cancelled_by: Admin user who cancelled
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            CancellationResponse DTO

        Raises:
            ValueError: If package not found
        """
        package = await self.package_repo.get_by_id_with_provider(package_id)

        if package is None:
            raise ValueError(f"Package {package_id} not found")

        package.cancelled_at = datetime.now(UTC)
        package.cancellation_effective_date = effective_date
        package.cancellation_reason = reason
        package.cancelled_by = cancelled_by

        # If effective date is today or in the past, mark as cancelled
        if effective_date <= date.today():
            package.status = PackageStatus.CANCELLED

        # Store notification data before commit to avoid extra SELECT after expire
        provider_name = package.provider.display_name if package.provider else "Unknown"
        package_name = package.license_type or "Unknown"
        seat_count = package.seats or 0

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PACKAGE_CANCEL,
                resource_type=ResourceType.LICENSE_PACKAGE,
                resource_id=package_id,
                user=user,
                request=request,
                details={
                    "effective_date": effective_date.isoformat() if effective_date else None,
                    "reason": reason,
                },
            )

        await self.session.commit()

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                cancelled_by_email = await self._get_user_email(cancelled_by)
                await self.notification_service.notify_package_cancelled(
                    provider_name=provider_name,
                    package_name=package_name,
                    seat_count=seat_count,
                    cancelled_by=cancelled_by_email,
                    cancellation_reason=reason,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send package cancellation notification: {e}")

        return CancellationResponse(
            id=package.id,
            cancelled_at=package.cancelled_at,
            cancellation_effective_date=package.cancellation_effective_date,
            cancellation_reason=package.cancellation_reason,
            cancelled_by=package.cancelled_by,
        )

    async def cancel_org_license(
        self,
        org_license_id: UUID,
        effective_date: date,
        reason: str | None,
        cancelled_by: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> CancellationResponse:
        """Cancel an organization license.

        Args:
            org_license_id: Organization license UUID
            effective_date: Date when cancellation becomes effective
            reason: Cancellation reason
            cancelled_by: Admin user who cancelled
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            CancellationResponse DTO

        Raises:
            ValueError: If org license not found
        """
        org_license = await self.org_license_repo.get_by_id_with_provider(org_license_id)

        if org_license is None:
            raise ValueError(f"Organization license {org_license_id} not found")

        org_license.cancelled_at = datetime.now(UTC)
        org_license.cancellation_effective_date = effective_date
        org_license.cancellation_reason = reason
        org_license.cancelled_by = cancelled_by

        # If effective date is today or in the past, mark as cancelled
        if effective_date <= date.today():
            org_license.status = OrgLicenseStatus.CANCELLED

        # Store notification data before commit to avoid extra SELECT after expire
        provider_name = org_license.provider.display_name if org_license.provider else "Unknown"
        org_license_name = org_license.name

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.ORG_LICENSE_CANCEL,
                resource_type=ResourceType.ORG_LICENSE,
                resource_id=org_license_id,
                user=user,
                request=request,
                details={
                    "effective_date": effective_date.isoformat() if effective_date else None,
                    "reason": reason,
                },
            )

        await self.session.commit()

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                cancelled_by_email = await self._get_user_email(cancelled_by)
                await self.notification_service.notify_org_license_cancelled(
                    provider_name=provider_name,
                    org_license_name=org_license_name,
                    cancelled_by=cancelled_by_email,
                    cancellation_reason=reason,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send org license cancellation notification: {e}")

        return CancellationResponse(
            id=org_license.id,
            cancelled_at=org_license.cancelled_at,
            cancellation_effective_date=org_license.cancellation_effective_date,
            cancellation_reason=org_license.cancellation_reason,
            cancelled_by=org_license.cancelled_by,
        )

    async def renew_license(
        self,
        license_id: UUID,
        new_expiration_date: date,
        renewed_by: UUID,
        clear_cancellation: bool = True,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> RenewalResponse:
        """Renew a license by setting a new expiration date.

        Args:
            license_id: License UUID
            new_expiration_date: New expiration date
            renewed_by: Admin user who renewed
            clear_cancellation: Whether to clear cancellation data
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            RenewalResponse DTO

        Raises:
            ValueError: If license not found
        """
        license_orm = await self.license_repo.get_by_id_with_provider(license_id)

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

        # Store notification data before commit to avoid extra SELECT after expire
        provider_name = license_orm.provider.display_name if license_orm.provider else "Unknown"
        license_type = license_orm.license_type
        external_user_id = license_orm.external_user_id

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.LICENSE_RENEW,
                resource_type=ResourceType.LICENSE,
                resource_id=license_id,
                user=user,
                request=request,
                details={
                    "new_expiration_date": new_expiration_date.isoformat(),
                    "clear_cancellation": clear_cancellation,
                },
            )

        await self.session.commit()

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                renewed_by_email = await self._get_user_email(renewed_by)
                await self.notification_service.notify_license_renewed(
                    provider_name=provider_name,
                    license_type=license_type,
                    user_email=external_user_id,
                    renewed_by=renewed_by_email,
                    new_expiration_date=new_expiration_date.isoformat()
                    if new_expiration_date
                    else None,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send license renewal notification: {e}")

        return RenewalResponse(
            success=True,
            message="License renewed successfully",
            expires_at=license_orm.expires_at.isoformat() if license_orm.expires_at else None,
            status=license_orm.status,
        )

    async def renew_package(
        self,
        package_id: UUID,
        new_contract_end: date,
        renewed_by: UUID,
        clear_cancellation: bool = True,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> RenewalResponse:
        """Renew a license package by setting a new contract end date.

        Args:
            package_id: Package UUID
            new_contract_end: New contract end date
            renewed_by: Admin user who renewed
            clear_cancellation: Whether to clear cancellation data
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            RenewalResponse DTO

        Raises:
            ValueError: If package not found
        """
        package = await self.package_repo.get_by_id_with_provider(package_id)

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

        # Store notification data before commit to avoid extra SELECT after expire
        provider_name = package.provider.display_name if package.provider else "Unknown"
        package_name = package.license_type or "Unknown"
        seat_count = package.total_seats or 0

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PACKAGE_RENEW,
                resource_type=ResourceType.LICENSE_PACKAGE,
                resource_id=package_id,
                user=user,
                request=request,
                details={
                    "new_contract_end": new_contract_end.isoformat(),
                    "clear_cancellation": clear_cancellation,
                },
            )

        await self.session.commit()

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                renewed_by_email = await self._get_user_email(renewed_by)
                await self.notification_service.notify_package_renewed(
                    provider_name=provider_name,
                    package_name=package_name,
                    seat_count=seat_count,
                    renewed_by=renewed_by_email,
                    new_contract_end=new_contract_end.isoformat() if new_contract_end else None,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send package renewal notification: {e}")

        return RenewalResponse(
            success=True,
            message="Package renewed successfully",
            contract_end=package.contract_end.isoformat() if package.contract_end else None,
            status=package.status,
        )

    async def set_license_needs_reorder(
        self,
        license_id: UUID,
        needs_reorder: bool,
        current_user_id: UUID | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> NeedsReorderResponse:
        """Set the needs_reorder flag for a license.

        Args:
            license_id: License UUID
            needs_reorder: Whether license needs reorder
            current_user_id: Current user ID (used as flagged_by when needs_reorder is True)
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            NeedsReorderResponse DTO

        Raises:
            ValueError: If license not found
        """
        flagged_by = current_user_id if needs_reorder else None
        license_orm = await self.license_repo.get_by_id_with_provider(license_id)

        if license_orm is None:
            raise ValueError(f"License {license_id} not found")

        license_orm.needs_reorder = needs_reorder

        # Store notification data before commit to avoid extra SELECT after expire
        provider_name = license_orm.provider.display_name if license_orm.provider else "Unknown"
        license_type = license_orm.license_type
        external_user_id = license_orm.external_user_id

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.LICENSE_NEEDS_REORDER,
                resource_type=ResourceType.LICENSE,
                resource_id=license_id,
                user=user,
                request=request,
                details={"needs_reorder": needs_reorder},
            )

        await self.session.commit()

        # Send notification when flagging for reorder (fire-and-forget)
        if needs_reorder and flagged_by:
            try:
                slack_token = await self._get_slack_token()
                if slack_token:
                    flagged_by_email = await self._get_user_email(flagged_by)
                    await self.notification_service.notify_license_needs_reorder(
                        provider_name=provider_name,
                        license_type=license_type,
                        user_email=external_user_id,
                        flagged_by=flagged_by_email,
                        slack_token=slack_token,
                    )
            except Exception as e:
                logger.warning(f"Failed to send license needs reorder notification: {e}")

        return NeedsReorderResponse(
            success=True,
            needs_reorder=license_orm.needs_reorder,
        )

    async def set_package_needs_reorder(
        self,
        package_id: UUID,
        needs_reorder: bool,
        current_user_id: UUID | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> NeedsReorderResponse:
        """Set the needs_reorder flag for a package.

        Args:
            package_id: Package UUID
            needs_reorder: Whether package needs reorder
            current_user_id: Current user ID (used as flagged_by when needs_reorder is True)
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            NeedsReorderResponse DTO

        Raises:
            ValueError: If package not found
        """
        flagged_by = current_user_id if needs_reorder else None
        package = await self.package_repo.get_by_id_with_provider(package_id)

        if package is None:
            raise ValueError(f"Package {package_id} not found")

        package.needs_reorder = needs_reorder

        # Store notification data before commit to avoid extra SELECT after expire
        provider_name = package.provider.display_name if package.provider else "Unknown"
        package_name = package.license_type or "Unknown"
        seat_count = package.total_seats or 0

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PACKAGE_NEEDS_REORDER,
                resource_type=ResourceType.LICENSE_PACKAGE,
                resource_id=package_id,
                user=user,
                request=request,
                details={"needs_reorder": needs_reorder},
            )

        await self.session.commit()

        # Send notification when flagging for reorder (fire-and-forget)
        if needs_reorder and flagged_by:
            try:
                slack_token = await self._get_slack_token()
                if slack_token:
                    flagged_by_email = await self._get_user_email(flagged_by)
                    await self.notification_service.notify_package_needs_reorder(
                        provider_name=provider_name,
                        package_name=package_name,
                        seat_count=seat_count,
                        flagged_by=flagged_by_email,
                        slack_token=slack_token,
                    )
            except Exception as e:
                logger.warning(f"Failed to send package needs reorder notification: {e}")

        return NeedsReorderResponse(
            success=True,
            needs_reorder=package.needs_reorder,
        )

    async def renew_org_license(
        self,
        org_license_id: UUID,
        renewed_by: UUID,
        new_renewal_date: date | None = None,
        new_expires_at: date | None = None,
        clear_cancellation: bool = True,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> RenewalResponse:
        """Renew an organization license by setting new renewal/expiration dates.

        Args:
            org_license_id: Organization license UUID
            renewed_by: Admin user who renewed
            new_renewal_date: New renewal date (optional)
            new_expires_at: New expiration date (optional)
            clear_cancellation: Whether to clear cancellation data
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            RenewalResponse DTO

        Raises:
            ValueError: If org license not found
        """
        org_license = await self.org_license_repo.get_by_id_with_provider(org_license_id)

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

        # Store notification data before commit to avoid extra SELECT after expire
        provider_name = org_license.provider.display_name if org_license.provider else "Unknown"
        org_license_name = org_license.name
        expiry_date = new_expires_at or new_renewal_date

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.ORG_LICENSE_RENEW,
                resource_type=ResourceType.ORG_LICENSE,
                resource_id=org_license_id,
                user=user,
                request=request,
                details={
                    "new_expiration_date": new_expires_at.isoformat() if new_expires_at else None,
                    "clear_cancellation": clear_cancellation,
                },
            )

        await self.session.commit()

        # Send notification (fire-and-forget)
        try:
            slack_token = await self._get_slack_token()
            if slack_token:
                renewed_by_email = await self._get_user_email(renewed_by)
                await self.notification_service.notify_org_license_renewed(
                    provider_name=provider_name,
                    org_license_name=org_license_name,
                    renewed_by=renewed_by_email,
                    new_expiration_date=expiry_date.isoformat() if expiry_date else None,
                    slack_token=slack_token,
                )
        except Exception as e:
            logger.warning(f"Failed to send org license renewal notification: {e}")

        return RenewalResponse(
            success=True,
            message="Organization license renewed successfully",
            renewal_date=org_license.renewal_date.isoformat()
            if org_license.renewal_date
            else None,
            expires_at=org_license.expires_at.isoformat() if org_license.expires_at else None,
            status=org_license.status,
        )

    async def set_org_license_needs_reorder(
        self,
        org_license_id: UUID,
        needs_reorder: bool,
        current_user_id: UUID | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> NeedsReorderResponse:
        """Set the needs_reorder flag for an organization license.

        Args:
            org_license_id: Organization license UUID
            needs_reorder: Whether org license needs reorder
            current_user_id: Current user ID (used as flagged_by when needs_reorder is True)
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            NeedsReorderResponse DTO

        Raises:
            ValueError: If org license not found
        """
        flagged_by = current_user_id if needs_reorder else None
        org_license = await self.org_license_repo.get_by_id_with_provider(org_license_id)

        if org_license is None:
            raise ValueError(f"Organization license {org_license_id} not found")

        org_license.needs_reorder = needs_reorder

        # Store notification data before commit to avoid extra SELECT after expire
        provider_name = org_license.provider.display_name if org_license.provider else "Unknown"
        org_license_name = org_license.name

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.ORG_LICENSE_NEEDS_REORDER,
                resource_type=ResourceType.ORG_LICENSE,
                resource_id=org_license_id,
                user=user,
                request=request,
                details={"needs_reorder": needs_reorder},
            )

        await self.session.commit()

        # Send notification when flagging for reorder (fire-and-forget)
        if needs_reorder and flagged_by:
            try:
                slack_token = await self._get_slack_token()
                if slack_token:
                    flagged_by_email = await self._get_user_email(flagged_by)
                    await self.notification_service.notify_org_license_needs_reorder(
                        provider_name=provider_name,
                        org_license_name=org_license_name,
                        flagged_by=flagged_by_email,
                        slack_token=slack_token,
                    )
            except Exception as e:
                logger.warning(f"Failed to send org license needs reorder notification: {e}")

        return NeedsReorderResponse(
            success=True,
            needs_reorder=org_license.needs_reorder,
        )
