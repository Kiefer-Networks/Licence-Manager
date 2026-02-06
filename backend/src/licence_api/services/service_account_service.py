"""Service Account Service for managing global service account patterns."""

from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.dto.license import LicenseResponse
from licence_api.models.dto.service_account import (
    ApplyLicenseTypesResponse,
    ApplyPatternsResponse,
    ServiceAccountLicenseTypeCreate,
    ServiceAccountLicenseTypeListResponse,
    ServiceAccountLicenseTypeResponse,
    ServiceAccountPatternCreate,
    ServiceAccountPatternListResponse,
    ServiceAccountPatternResponse,
)
from licence_api.models.orm.service_account_license_type import ServiceAccountLicenseTypeORM
from licence_api.models.orm.service_account_pattern import ServiceAccountPatternORM
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.service_account_license_type_repository import (
    ServiceAccountLicenseTypeRepository,
)
from licence_api.repositories.service_account_pattern_repository import (
    ServiceAccountPatternRepository,
)
from licence_api.repositories.user_repository import UserRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType


class ServiceAccountService:
    """Service for managing global service account patterns."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.pattern_repo = ServiceAccountPatternRepository(session)
        self.license_type_repo = ServiceAccountLicenseTypeRepository(session)
        self.license_repo = LicenseRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.user_repo = UserRepository(session)
        self.audit_service = AuditService(session)

    def _pattern_to_response(
        self,
        pattern: ServiceAccountPatternORM,
        match_count: int = 0,
        owner_name: str | None = None,
        creator_name: str | None = None,
    ) -> ServiceAccountPatternResponse:
        """Convert ORM pattern to response DTO."""
        return ServiceAccountPatternResponse(
            id=pattern.id,
            email_pattern=pattern.email_pattern,
            name=pattern.name,
            owner_id=pattern.owner_id,
            owner_name=owner_name or (pattern.owner.full_name if pattern.owner else None),
            notes=pattern.notes,
            created_at=pattern.created_at,
            created_by=pattern.created_by,
            created_by_name=creator_name or (pattern.creator.name if pattern.creator else None),
            match_count=match_count,
        )

    async def get_all_patterns(self) -> ServiceAccountPatternListResponse:
        """Get all service account patterns with match counts.

        Returns:
            ServiceAccountPatternListResponse with all patterns
        """
        patterns_with_counts = await self.pattern_repo.get_all_with_match_counts()

        items = []
        for pattern, match_count in patterns_with_counts:
            items.append(self._pattern_to_response(pattern, match_count))

        return ServiceAccountPatternListResponse(
            items=items,
            total=len(items),
        )

    async def get_pattern_by_id(self, pattern_id: UUID) -> ServiceAccountPatternResponse | None:
        """Get a single pattern by ID.

        Args:
            pattern_id: Pattern UUID

        Returns:
            ServiceAccountPatternResponse or None if not found
        """
        pattern = await self.pattern_repo.get_by_id(pattern_id)
        if not pattern:
            return None

        match_count = await self.pattern_repo.get_match_count(pattern_id)
        return self._pattern_to_response(pattern, match_count)

    async def create_pattern(
        self,
        data: ServiceAccountPatternCreate,
        created_by: UUID | None = None,
        request: Request | None = None,
    ) -> ServiceAccountPatternResponse:
        """Create a new service account pattern.

        Args:
            data: Pattern creation data
            created_by: Admin user ID who created the pattern
            request: HTTP request for audit logging

        Returns:
            Created ServiceAccountPatternResponse
        """
        pattern = await self.pattern_repo.create(
            email_pattern=data.email_pattern,
            name=data.name,
            owner_id=data.owner_id,
            notes=data.notes,
            created_by=created_by,
        )

        # Audit log the creation
        await self.audit_service.log(
            action=AuditAction.SERVICE_ACCOUNT_PATTERN_CREATE,
            resource_type=ResourceType.SERVICE_ACCOUNT_PATTERN,
            resource_id=pattern.id,
            admin_user_id=created_by,
            changes={
                "email_pattern": data.email_pattern,
                "name": data.name,
                "owner_id": str(data.owner_id) if data.owner_id else None,
            },
            request=request,
        )

        await self.session.commit()

        match_count = await self.pattern_repo.get_match_count(pattern.id)
        return self._pattern_to_response(pattern, match_count)

    async def delete_pattern(
        self,
        pattern_id: UUID,
        admin_user_id: UUID | None = None,
        request: Request | None = None,
        pattern_info: dict | None = None,
    ) -> bool:
        """Delete a service account pattern.

        Args:
            pattern_id: Pattern UUID
            admin_user_id: Admin user deleting the pattern
            request: HTTP request for audit logging
            pattern_info: Pattern info for audit log (email_pattern, name)

        Returns:
            True if deleted, False if not found
        """
        result = await self.pattern_repo.delete(pattern_id)

        if result and admin_user_id:
            # Audit log the deletion
            await self.audit_service.log(
                action=AuditAction.SERVICE_ACCOUNT_PATTERN_DELETE,
                resource_type=ResourceType.SERVICE_ACCOUNT_PATTERN,
                resource_id=pattern_id,
                admin_user_id=admin_user_id,
                changes=pattern_info or {},
                request=request,
            )
            await self.session.commit()

        return result

    async def apply_patterns_to_all_licenses(
        self,
        admin_user_id: UUID | None = None,
        request: Request | None = None,
    ) -> ApplyPatternsResponse:
        """Apply all patterns to all licenses.

        Marks matching licenses as service accounts.

        Args:
            admin_user_id: Admin user applying patterns
            request: HTTP request for audit logging

        Returns:
            ApplyPatternsResponse with count of updated licenses
        """
        patterns = await self.pattern_repo.get_all()
        updated_count = 0
        patterns_applied = 0

        for pattern in patterns:
            matching_licenses = await self.pattern_repo.find_matching_licenses(pattern)
            pattern_updates = 0

            for license in matching_licenses:
                # Only update if not already marked as service account
                if not license.is_service_account:
                    license.is_service_account = True
                    license.service_account_name = pattern.name
                    license.service_account_owner_id = pattern.owner_id
                    updated_count += 1
                    pattern_updates += 1

            if pattern_updates > 0:
                patterns_applied += 1

        # Audit log the application
        if admin_user_id:
            await self.audit_service.log(
                action=AuditAction.SERVICE_ACCOUNT_PATTERNS_APPLY,
                resource_type=ResourceType.SERVICE_ACCOUNT_PATTERN,
                admin_user_id=admin_user_id,
                changes={
                    "updated_count": updated_count,
                    "patterns_applied": patterns_applied,
                },
                request=request,
            )

        await self.session.commit()

        return ApplyPatternsResponse(
            updated_count=updated_count,
            patterns_applied=patterns_applied,
        )

    async def check_and_mark_license(
        self, license_external_user_id: str
    ) -> ServiceAccountPatternORM | None:
        """Check if an email matches any pattern and return the matching pattern.

        This method is used during sync to automatically mark licenses as service accounts.

        Args:
            license_external_user_id: The email address to check

        Returns:
            The matching pattern if found, None otherwise
        """
        return await self.pattern_repo.matches_email(license_external_user_id)

    async def get_service_account_licenses(
        self,
        search: str | None = None,
        provider_id: UUID | None = None,
        sort_by: str = "external_user_id",
        sort_dir: str = "asc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[LicenseResponse], int]:
        """Get all licenses marked as service accounts.

        Args:
            search: Search by email
            provider_id: Filter by provider
            sort_by: Column to sort by
            sort_dir: Sort direction
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (licenses, total_count)
        """
        offset = (page - 1) * page_size

        results, total = await self.license_repo.get_all_with_details(
            provider_id=provider_id,
            search=search,
            service_accounts_only=True,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=offset,
            limit=page_size,
        )

        items = []
        for license_orm, provider_orm, employee_orm in results:
            # Get service account owner name
            service_account_owner_name = None
            if license_orm.service_account_owner_id:
                owner = await self.employee_repo.get_by_id(license_orm.service_account_owner_id)
                service_account_owner_name = owner.full_name if owner else None

            items.append(
                LicenseResponse(
                    id=license_orm.id,
                    provider_id=license_orm.provider_id,
                    provider_name=provider_orm.display_name,
                    employee_id=license_orm.employee_id,
                    employee_email=employee_orm.email if employee_orm else None,
                    employee_name=employee_orm.full_name if employee_orm else None,
                    external_user_id=license_orm.external_user_id,
                    license_type=license_orm.license_type,
                    status=license_orm.status,
                    assigned_at=license_orm.assigned_at,
                    last_activity_at=license_orm.last_activity_at,
                    monthly_cost=license_orm.monthly_cost,
                    currency=license_orm.currency,
                    metadata=license_orm.extra_data or {},
                    synced_at=license_orm.synced_at,
                    is_service_account=license_orm.is_service_account,
                    service_account_name=license_orm.service_account_name,
                    service_account_owner_id=license_orm.service_account_owner_id,
                    service_account_owner_name=service_account_owner_name,
                )
            )

        return items, total

    async def create_pattern_from_email(
        self,
        email: str,
        name: str | None = None,
        owner_id: UUID | None = None,
        notes: str | None = None,
        created_by: UUID | None = None,
    ) -> ServiceAccountPatternResponse | None:
        """Create a pattern from an exact email address.

        Used when marking a license as service account with "apply_globally" option.
        Returns None if pattern already exists.

        Args:
            email: The email address to add as pattern
            name: Optional name for the pattern
            owner_id: Optional owner employee ID
            notes: Optional notes
            created_by: Admin user ID

        Returns:
            Created pattern or None if already exists
        """
        # Check if pattern already exists
        existing = await self.pattern_repo.get_by_email_pattern(email)
        if existing:
            return None

        return await self.create_pattern(
            data=ServiceAccountPatternCreate(
                email_pattern=email,
                name=name,
                owner_id=owner_id,
                notes=notes,
            ),
            created_by=created_by,
        )

    # License Type Methods
    def _license_type_to_response(
        self,
        entry: ServiceAccountLicenseTypeORM,
        match_count: int = 0,
        owner_name: str | None = None,
        creator_name: str | None = None,
    ) -> ServiceAccountLicenseTypeResponse:
        """Convert ORM license type entry to response DTO."""
        return ServiceAccountLicenseTypeResponse(
            id=entry.id,
            license_type=entry.license_type,
            name=entry.name,
            owner_id=entry.owner_id,
            owner_name=owner_name or (entry.owner.full_name if entry.owner else None),
            notes=entry.notes,
            created_at=entry.created_at,
            created_by=entry.created_by,
            created_by_name=creator_name or (entry.creator.name if entry.creator else None),
            match_count=match_count,
        )

    async def get_all_license_types(self) -> ServiceAccountLicenseTypeListResponse:
        """Get all service account license types with match counts.

        Returns:
            ServiceAccountLicenseTypeListResponse with all entries
        """
        entries_with_counts = await self.license_type_repo.get_all_with_match_counts()

        items = []
        for entry, match_count in entries_with_counts:
            items.append(self._license_type_to_response(entry, match_count))

        return ServiceAccountLicenseTypeListResponse(
            items=items,
            total=len(items),
        )

    async def get_license_type_by_id(
        self, entry_id: UUID
    ) -> ServiceAccountLicenseTypeResponse | None:
        """Get a single license type entry by ID.

        Args:
            entry_id: Entry UUID

        Returns:
            ServiceAccountLicenseTypeResponse or None if not found
        """
        entry = await self.license_type_repo.get_by_id(entry_id)
        if not entry:
            return None

        match_count = await self.license_type_repo.get_match_count(entry_id)
        return self._license_type_to_response(entry, match_count)

    async def create_license_type(
        self,
        data: ServiceAccountLicenseTypeCreate,
        created_by: UUID | None = None,
        request: Request | None = None,
    ) -> ServiceAccountLicenseTypeResponse:
        """Create a new service account license type.

        Args:
            data: License type creation data
            created_by: Admin user ID who created the entry
            request: HTTP request for audit logging

        Returns:
            Created ServiceAccountLicenseTypeResponse
        """
        entry = await self.license_type_repo.create(
            license_type=data.license_type,
            name=data.name,
            owner_id=data.owner_id,
            notes=data.notes,
            created_by=created_by,
        )

        # Audit log the creation
        await self.audit_service.log(
            action=AuditAction.SERVICE_ACCOUNT_LICENSE_TYPE_CREATE,
            resource_type=ResourceType.SERVICE_ACCOUNT_LICENSE_TYPE,
            resource_id=entry.id,
            admin_user_id=created_by,
            changes={
                "license_type": data.license_type,
                "name": data.name,
                "owner_id": str(data.owner_id) if data.owner_id else None,
            },
            request=request,
        )

        await self.session.commit()

        match_count = await self.license_type_repo.get_match_count(entry.id)
        return self._license_type_to_response(entry, match_count)

    async def delete_license_type(
        self,
        entry_id: UUID,
        admin_user_id: UUID | None = None,
        request: Request | None = None,
        entry_info: dict | None = None,
    ) -> bool:
        """Delete a service account license type.

        Args:
            entry_id: Entry UUID
            admin_user_id: Admin user deleting the entry
            request: HTTP request for audit logging
            entry_info: Entry info for audit log (license_type, name)

        Returns:
            True if deleted, False if not found
        """
        result = await self.license_type_repo.delete(entry_id)

        if result and admin_user_id:
            # Audit log the deletion
            await self.audit_service.log(
                action=AuditAction.SERVICE_ACCOUNT_LICENSE_TYPE_DELETE,
                resource_type=ResourceType.SERVICE_ACCOUNT_LICENSE_TYPE,
                resource_id=entry_id,
                admin_user_id=admin_user_id,
                changes=entry_info or {},
                request=request,
            )
            await self.session.commit()

        return result

    async def apply_license_types_to_all_licenses(
        self,
        admin_user_id: UUID | None = None,
        request: Request | None = None,
    ) -> ApplyLicenseTypesResponse:
        """Apply all license type rules to all licenses.

        Marks matching licenses as service accounts.

        Args:
            admin_user_id: Admin user applying license types
            request: HTTP request for audit logging

        Returns:
            ApplyLicenseTypesResponse with count of updated licenses
        """
        entries = await self.license_type_repo.get_all()
        updated_count = 0
        license_types_applied = 0

        for entry in entries:
            matching_licenses = await self.license_type_repo.find_matching_licenses(entry)
            entry_updates = 0

            for license in matching_licenses:
                # Only update if not already marked as service account
                if not license.is_service_account:
                    license.is_service_account = True
                    license.service_account_name = entry.name
                    license.service_account_owner_id = entry.owner_id
                    updated_count += 1
                    entry_updates += 1

            if entry_updates > 0:
                license_types_applied += 1

        # Audit log the application
        if admin_user_id:
            await self.audit_service.log(
                action=AuditAction.SERVICE_ACCOUNT_LICENSE_TYPES_APPLY,
                resource_type=ResourceType.SERVICE_ACCOUNT_LICENSE_TYPE,
                admin_user_id=admin_user_id,
                changes={
                    "updated_count": updated_count,
                    "license_types_applied": license_types_applied,
                },
                request=request,
            )

        await self.session.commit()

        return ApplyLicenseTypesResponse(
            updated_count=updated_count,
            license_types_applied=license_types_applied,
        )

    async def check_license_type_for_service_account(
        self, license_type: str
    ) -> ServiceAccountLicenseTypeORM | None:
        """Check if a license type matches any license type rule.

        This method is used during sync to automatically mark licenses as service accounts.

        Args:
            license_type: The license type to check

        Returns:
            The matching entry if found, None otherwise
        """
        return await self.license_type_repo.matches_license_type(license_type)
