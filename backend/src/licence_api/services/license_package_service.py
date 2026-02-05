"""License package service for managing license packages."""

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.dto.license_package import (
    LicensePackageCreate,
    LicensePackageListResponse,
    LicensePackageResponse,
    LicensePackageUpdate,
)
from licence_api.repositories.license_package_repository import LicensePackageRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType

if TYPE_CHECKING:
    from licence_api.models.orm.license_package import LicensePackageORM


class LicensePackageService:
    """Service for managing license packages."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.package_repo = LicensePackageRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.audit_service = AuditService(session)

    def _build_package_response(
        self,
        package: "LicensePackageORM",
        assigned_seats: int,
    ) -> LicensePackageResponse:
        """Build license package response with utilization stats."""
        available_seats = max(0, package.total_seats - assigned_seats)
        utilization = (assigned_seats / package.total_seats * 100) if package.total_seats > 0 else 0
        total_cost = (
            package.cost_per_seat * package.total_seats
            if package.cost_per_seat
            else None
        )

        return LicensePackageResponse(
            id=package.id,
            provider_id=package.provider_id,
            license_type=package.license_type,
            display_name=package.display_name,
            total_seats=package.total_seats,
            assigned_seats=assigned_seats,
            available_seats=available_seats,
            utilization_percent=round(utilization, 1),
            cost_per_seat=package.cost_per_seat,
            total_monthly_cost=total_cost,
            billing_cycle=package.billing_cycle,
            payment_frequency=package.payment_frequency,
            currency=package.currency,
            contract_start=package.contract_start,
            contract_end=package.contract_end,
            auto_renew=package.auto_renew,
            notes=package.notes,
            created_at=package.created_at,
            updated_at=package.updated_at,
        )

    async def list_packages(self, provider_id: UUID) -> LicensePackageListResponse:
        """List all license packages for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            LicensePackageListResponse

        Raises:
            ValueError: If provider not found
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if not provider:
            raise ValueError("Provider not found")

        packages = await self.package_repo.get_by_provider(provider_id)
        assigned_counts = await self.package_repo.get_all_assigned_seats_counts(provider_id)

        items = [
            self._build_package_response(p, assigned_counts.get(p.license_type, 0))
            for p in packages
        ]

        return LicensePackageListResponse(items=items, total=len(items))

    async def create_package(
        self,
        provider_id: UUID,
        data: LicensePackageCreate,
        admin_user_id: UUID,
        request: Request | None = None,
    ) -> LicensePackageResponse:
        """Create a new license package.

        Args:
            provider_id: Provider UUID
            data: Package creation data
            admin_user_id: Admin user creating the package
            request: HTTP request for audit logging

        Returns:
            Created LicensePackageResponse

        Raises:
            ValueError: If provider not found or package already exists
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if not provider:
            raise ValueError("Provider not found")

        # Check if package already exists for this type
        existing = await self.package_repo.get_by_provider_and_type(provider_id, data.license_type)
        if existing:
            raise ValueError(f"License package for type '{data.license_type}' already exists")

        package = await self.package_repo.create_package(
            provider_id=provider_id,
            license_type=data.license_type,
            display_name=data.display_name,
            total_seats=data.total_seats,
            cost_per_seat=data.cost_per_seat,
            billing_cycle=data.billing_cycle,
            payment_frequency=data.payment_frequency,
            currency=data.currency,
            contract_start=data.contract_start,
            contract_end=data.contract_end,
            auto_renew=data.auto_renew,
            notes=data.notes,
        )

        # Audit log
        await self.audit_service.log(
            action=AuditAction.LICENSE_PACKAGE_CREATE,
            resource_type=ResourceType.LICENSE,
            resource_id=package.id,
            admin_user_id=admin_user_id,
            changes={
                "provider_id": str(provider_id),
                "license_type": data.license_type,
                "display_name": data.display_name,
                "total_seats": data.total_seats,
            },
            request=request,
        )

        await self.session.commit()

        assigned = await self.package_repo.get_assigned_seats_count(provider_id, data.license_type)
        return self._build_package_response(package, assigned)

    async def update_package(
        self,
        provider_id: UUID,
        package_id: UUID,
        data: LicensePackageUpdate,
        admin_user_id: UUID,
        request: Request | None = None,
    ) -> LicensePackageResponse:
        """Update a license package.

        Args:
            provider_id: Provider UUID
            package_id: Package UUID
            data: Package update data
            admin_user_id: Admin user updating the package
            request: HTTP request for audit logging

        Returns:
            Updated LicensePackageResponse

        Raises:
            ValueError: If package not found
        """
        package = await self.package_repo.get_by_provider_and_id(provider_id, package_id)
        if not package:
            raise ValueError("License package not found")

        update_data = data.model_dump(exclude_unset=True)

        # Capture changes for audit
        changes = {k: v for k, v in update_data.items()}

        package = await self.package_repo.update_package(package, **update_data)

        # Audit log
        await self.audit_service.log(
            action=AuditAction.LICENSE_PACKAGE_UPDATE,
            resource_type=ResourceType.LICENSE,
            resource_id=package.id,
            admin_user_id=admin_user_id,
            changes=changes,
            request=request,
        )

        await self.session.commit()

        assigned = await self.package_repo.get_assigned_seats_count(provider_id, package.license_type)
        return self._build_package_response(package, assigned)

    async def delete_package(
        self,
        provider_id: UUID,
        package_id: UUID,
        admin_user_id: UUID,
        request: Request | None = None,
    ) -> None:
        """Delete a license package.

        Args:
            provider_id: Provider UUID
            package_id: Package UUID
            admin_user_id: Admin user deleting the package
            request: HTTP request for audit logging

        Raises:
            ValueError: If package not found
        """
        package = await self.package_repo.get_by_provider_and_id(provider_id, package_id)
        if not package:
            raise ValueError("License package not found")

        # Capture info for audit before deletion
        license_type = package.license_type

        await self.package_repo.delete_package(package)

        # Audit log
        await self.audit_service.log(
            action=AuditAction.LICENSE_PACKAGE_DELETE,
            resource_type=ResourceType.LICENSE,
            resource_id=package_id,
            admin_user_id=admin_user_id,
            changes={
                "provider_id": str(provider_id),
                "license_type": license_type,
            },
            request=request,
        )

        await self.session.commit()
