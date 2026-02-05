"""Organization license service for managing organization-wide licenses."""

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.dto.organization_license import (
    OrganizationLicenseCreate,
    OrganizationLicenseListResponse,
    OrganizationLicenseResponse,
    OrganizationLicenseUpdate,
)
from licence_api.repositories.organization_license_repository import OrganizationLicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType

if TYPE_CHECKING:
    from licence_api.models.orm.organization_license import OrganizationLicenseORM


class OrganizationLicenseService:
    """Service for managing organization-wide licenses."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.license_repo = OrganizationLicenseRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.audit_service = AuditService(session)

    def _build_response(self, lic: "OrganizationLicenseORM") -> OrganizationLicenseResponse:
        """Build organization license response from ORM."""
        return OrganizationLicenseResponse(
            id=lic.id,
            provider_id=lic.provider_id,
            name=lic.name,
            license_type=lic.license_type,
            quantity=lic.quantity,
            unit=lic.unit,
            monthly_cost=lic.monthly_cost,
            currency=lic.currency,
            billing_cycle=lic.billing_cycle,
            renewal_date=lic.renewal_date,
            notes=lic.notes,
            created_at=lic.created_at,
            updated_at=lic.updated_at,
        )

    async def list_licenses(self, provider_id: UUID) -> OrganizationLicenseListResponse:
        """List all organization licenses for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            OrganizationLicenseListResponse

        Raises:
            ValueError: If provider not found
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if not provider:
            raise ValueError("Provider not found")

        licenses = await self.license_repo.get_by_provider(provider_id)
        total_cost = await self.license_repo.get_total_monthly_cost(provider_id)

        items = [self._build_response(lic) for lic in licenses]

        return OrganizationLicenseListResponse(
            items=items,
            total=len(items),
            total_monthly_cost=total_cost,
        )

    async def create_license(
        self,
        provider_id: UUID,
        data: OrganizationLicenseCreate,
        admin_user_id: UUID,
        request: Request | None = None,
    ) -> OrganizationLicenseResponse:
        """Create a new organization license.

        Args:
            provider_id: Provider UUID
            data: License creation data
            admin_user_id: Admin user creating the license
            request: HTTP request for audit logging

        Returns:
            Created OrganizationLicenseResponse

        Raises:
            ValueError: If provider not found
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if not provider:
            raise ValueError("Provider not found")

        license_orm = await self.license_repo.create_organization_license(
            provider_id=provider_id,
            name=data.name,
            license_type=data.license_type,
            quantity=data.quantity,
            unit=data.unit,
            monthly_cost=data.monthly_cost,
            currency=data.currency,
            billing_cycle=data.billing_cycle,
            renewal_date=data.renewal_date,
            notes=data.notes,
        )

        # Audit log
        await self.audit_service.log(
            action=AuditAction.LICENSE_CREATE,
            resource_type=ResourceType.LICENSE,
            resource_id=license_orm.id,
            admin_user_id=admin_user_id,
            changes={
                "provider_id": str(provider_id),
                "name": data.name,
                "license_type": data.license_type,
                "quantity": data.quantity,
                "monthly_cost": str(data.monthly_cost) if data.monthly_cost else None,
            },
            request=request,
        )

        await self.session.commit()

        return self._build_response(license_orm)

    async def update_license(
        self,
        provider_id: UUID,
        license_id: UUID,
        data: OrganizationLicenseUpdate,
        admin_user_id: UUID,
        request: Request | None = None,
    ) -> OrganizationLicenseResponse:
        """Update an organization license.

        Args:
            provider_id: Provider UUID
            license_id: License UUID
            data: License update data
            admin_user_id: Admin user updating the license
            request: HTTP request for audit logging

        Returns:
            Updated OrganizationLicenseResponse

        Raises:
            ValueError: If license not found
        """
        license_orm = await self.license_repo.get_by_provider_and_id(provider_id, license_id)
        if not license_orm:
            raise ValueError("Organization license not found")

        update_data = data.model_dump(exclude_unset=True)
        license_orm = await self.license_repo.update_organization_license(license_orm, **update_data)

        # Audit log
        await self.audit_service.log(
            action=AuditAction.LICENSE_UPDATE,
            resource_type=ResourceType.LICENSE,
            resource_id=license_id,
            admin_user_id=admin_user_id,
            changes=update_data,
            request=request,
        )

        await self.session.commit()

        return self._build_response(license_orm)

    async def delete_license(
        self,
        provider_id: UUID,
        license_id: UUID,
        admin_user_id: UUID,
        request: Request | None = None,
    ) -> None:
        """Delete an organization license.

        Args:
            provider_id: Provider UUID
            license_id: License UUID
            admin_user_id: Admin user deleting the license
            request: HTTP request for audit logging

        Raises:
            ValueError: If license not found
        """
        license_orm = await self.license_repo.get_by_provider_and_id(provider_id, license_id)
        if not license_orm:
            raise ValueError("Organization license not found")

        # Capture info for audit before deletion
        license_name = license_orm.name

        await self.license_repo.delete_organization_license(license_orm)

        # Audit log
        await self.audit_service.log(
            action=AuditAction.LICENSE_DELETE,
            resource_type=ResourceType.LICENSE,
            resource_id=license_id,
            admin_user_id=admin_user_id,
            changes={
                "provider_id": str(provider_id),
                "name": license_name,
            },
            request=request,
        )

        await self.session.commit()
