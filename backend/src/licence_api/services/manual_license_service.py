"""Manual license service for managing licenses without API."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.license import LicenseResponse
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType


class ManualLicenseService:
    """Service for managing manual licenses."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.license_repo = LicenseRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.audit_service = AuditService(session)

    async def _build_license_response(self, license_orm, provider=None) -> LicenseResponse:
        """Build a LicenseResponse from ORM object."""
        if provider is None:
            provider = await self.provider_repo.get_by_id(license_orm.provider_id)

        employee = None
        if license_orm.employee_id:
            employee = await self.employee_repo.get_by_id(license_orm.employee_id)

        return LicenseResponse(
            id=license_orm.id,
            provider_id=license_orm.provider_id,
            provider_name=provider.display_name if provider else "Unknown",
            employee_id=license_orm.employee_id,
            employee_email=employee.email if employee else None,
            employee_name=employee.full_name if employee else None,
            external_user_id=license_orm.external_user_id,
            license_type=license_orm.license_type,
            status=license_orm.status,
            assigned_at=license_orm.assigned_at,
            last_activity_at=license_orm.last_activity_at,
            monthly_cost=license_orm.monthly_cost,
            currency=license_orm.currency,
            metadata=license_orm.extra_data or {},
            synced_at=license_orm.synced_at,
        )

    async def create_licenses(
        self,
        provider_id: UUID,
        quantity: int = 1,
        license_type: str | None = None,
        license_key: str | None = None,
        monthly_cost: Decimal | None = None,
        currency: str = "EUR",
        valid_until: datetime | None = None,
        notes: str | None = None,
        employee_id: UUID | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> list[LicenseResponse]:
        """Create one or more manual licenses.

        Args:
            provider_id: Provider UUID
            quantity: Number of licenses to create
            license_type: Optional license type
            license_key: Optional license key
            monthly_cost: Optional monthly cost
            currency: Currency code
            valid_until: Optional expiration date
            notes: Optional notes
            employee_id: Optional employee to assign
            user: Admin user creating the licenses
            request: HTTP request for audit logging

        Returns:
            List of created LicenseResponse objects

        Raises:
            ValueError: If provider not found or not a manual provider
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if not provider:
            raise ValueError("Provider not found")

        provider_config = provider.config or {}
        if provider_config.get("provider_type") != "manual":
            raise ValueError("Can only add manual licenses to manual providers")

        created_licenses = []
        now = datetime.now(UTC)

        for i in range(quantity):
            if license_key and quantity == 1:
                external_id = license_key
            else:
                external_id = f"manual-{uuid4().hex[:12]}"

            metadata = {
                "manual_entry": True,
                "created_by": str(user.id) if user and user.id else "admin",
            }
            if license_key and quantity == 1:
                metadata["license_key"] = license_key
            if valid_until:
                metadata["valid_until"] = valid_until.isoformat()
            if notes:
                metadata["notes"] = notes

            license_orm = await self.license_repo.create(
                provider_id=provider_id,
                employee_id=employee_id,
                external_user_id=external_id,
                license_type=license_type,
                status="active",
                assigned_at=now if employee_id else None,
                last_activity_at=None,
                monthly_cost=monthly_cost,
                currency=currency,
                extra_data=metadata,
                synced_at=now,
            )

            response = await self._build_license_response(license_orm, provider)
            created_licenses.append(response)

            # Audit log each license
            if user:
                await self.audit_service.log(
                    action=AuditAction.LICENSE_CREATE,
                    resource_type=ResourceType.LICENSE,
                    resource_id=license_orm.id,
                    user=user,
                    request=request,
                    details={
                        "provider_id": str(provider_id),
                        "license_type": license_type,
                        "employee_id": str(employee_id) if employee_id else None,
                        "manual_entry": True,
                    },
                )

        await self.session.commit()
        return created_licenses

    async def create_licenses_bulk(
        self,
        provider_id: UUID,
        license_keys: list[str],
        license_type: str | None = None,
        monthly_cost: Decimal | None = None,
        currency: str = "EUR",
        valid_until: datetime | None = None,
        notes: str | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> list[LicenseResponse]:
        """Create multiple manual licenses with individual keys.

        Args:
            provider_id: Provider UUID
            license_keys: List of license keys
            license_type: Optional license type
            monthly_cost: Optional monthly cost
            currency: Currency code
            valid_until: Optional expiration date
            notes: Optional notes
            user: Admin user creating the licenses
            request: HTTP request for audit logging

        Returns:
            List of created LicenseResponse objects

        Raises:
            ValueError: If provider not found, not manual, or too many keys
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if not provider:
            raise ValueError("Provider not found")

        provider_config = provider.config or {}
        if provider_config.get("provider_type") != "manual":
            raise ValueError("Can only add manual licenses to manual providers")

        if len(license_keys) > 100:
            raise ValueError("Maximum 100 licenses per bulk operation")

        created_licenses = []
        now = datetime.now(UTC)

        for license_key in license_keys:
            metadata = {
                "manual_entry": True,
                "license_key": license_key,
                "created_by": str(user.id) if user and user.id else "admin",
            }
            if valid_until:
                metadata["valid_until"] = valid_until.isoformat()
            if notes:
                metadata["notes"] = notes

            license_orm = await self.license_repo.create(
                provider_id=provider_id,
                employee_id=None,
                external_user_id=license_key,
                license_type=license_type,
                status="active",
                assigned_at=None,
                last_activity_at=None,
                monthly_cost=monthly_cost,
                currency=currency,
                extra_data=metadata,
                synced_at=now,
            )

            response = await self._build_license_response(license_orm, provider)
            created_licenses.append(response)

        # Audit log bulk create
        if user:
            await self.audit_service.log(
                action=AuditAction.LICENSE_BULK_CREATE,
                resource_type=ResourceType.LICENSE,
                resource_id=None,
                user=user,
                request=request,
                details={
                    "provider_id": str(provider_id),
                    "license_type": license_type,
                    "count": len(created_licenses),
                    "manual_entry": True,
                },
            )

        await self.session.commit()
        return created_licenses

    async def update_license(
        self,
        license_id: UUID,
        license_type: str | None = None,
        license_key: str | None = None,
        monthly_cost: Decimal | None = None,
        currency: str | None = None,
        valid_until: datetime | None = None,
        notes: str | None = None,
        employee_id: UUID | None = None,
        unassign: bool = False,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> LicenseResponse:
        """Update a manual license.

        Args:
            license_id: License UUID
            license_type: Optional new license type
            license_key: Optional new license key
            monthly_cost: Optional new monthly cost
            currency: Optional new currency
            valid_until: Optional new expiration date
            notes: Optional new notes
            employee_id: Optional employee to assign
            unassign: If True, unassign from current employee
            user: Admin user making the update
            request: HTTP request for audit logging

        Returns:
            Updated LicenseResponse

        Raises:
            ValueError: If license not found or not a manual license
        """
        license_orm = await self.license_repo.get_by_id(license_id)
        if not license_orm:
            raise ValueError("License not found")

        metadata = license_orm.extra_data or {}
        if not metadata.get("manual_entry"):
            raise ValueError("Can only update manual licenses")

        update_data = {}

        if license_type is not None:
            update_data["license_type"] = license_type

        if monthly_cost is not None:
            update_data["monthly_cost"] = monthly_cost

        if currency is not None:
            update_data["currency"] = currency

        if employee_id is not None:
            update_data["employee_id"] = employee_id
            update_data["status"] = "active"
            update_data["assigned_at"] = datetime.now(UTC)
        elif unassign:
            update_data["employee_id"] = None
            update_data["status"] = "unassigned"
            update_data["assigned_at"] = None

        # Update metadata
        if license_key is not None:
            metadata["license_key"] = license_key
        if valid_until is not None:
            metadata["valid_until"] = valid_until.isoformat()
        if notes is not None:
            metadata["notes"] = notes

        update_data["extra_data"] = metadata

        license_orm = await self.license_repo.update(license_id, **update_data)

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.LICENSE_UPDATE,
                resource_type=ResourceType.LICENSE,
                resource_id=license_id,
                user=user,
                request=request,
                details={"changes": list(update_data.keys()), "manual_entry": True},
            )

        await self.session.commit()
        return await self._build_license_response(license_orm)

    async def unassign_license(
        self,
        license_id: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> LicenseResponse:
        """Unassign a manual license from an employee.

        Args:
            license_id: License UUID
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            Updated LicenseResponse

        Raises:
            ValueError: If license not found
        """
        license_orm = await self.license_repo.get_by_id(license_id)
        if not license_orm:
            raise ValueError("License not found")

        old_employee_id = license_orm.employee_id

        license_orm = await self.license_repo.update(
            license_id,
            employee_id=None,
            status="unassigned",
            assigned_at=None,
        )

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.LICENSE_UNASSIGN,
                resource_type=ResourceType.LICENSE,
                resource_id=license_id,
                user=user,
                request=request,
                details={"previous_employee_id": str(old_employee_id) if old_employee_id else None},
            )

        await self.session.commit()
        return await self._build_license_response(license_orm)

    async def delete_license(
        self,
        license_id: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> None:
        """Delete a manual license.

        Args:
            license_id: License UUID
            user: Admin user making the deletion
            request: HTTP request for audit logging

        Raises:
            ValueError: If license not found or not a manual license
        """
        license_orm = await self.license_repo.get_by_id(license_id)
        if not license_orm:
            raise ValueError("License not found")

        metadata = license_orm.extra_data or {}
        if not metadata.get("manual_entry"):
            raise ValueError("Can only delete manual licenses")

        provider_id = license_orm.provider_id

        await self.license_repo.delete(license_id)

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.LICENSE_DELETE,
                resource_type=ResourceType.LICENSE,
                resource_id=license_id,
                user=user,
                request=request,
                details={"provider_id": str(provider_id), "manual_entry": True},
            )

        await self.session.commit()
