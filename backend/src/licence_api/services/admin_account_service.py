"""Admin Account Service for managing admin account patterns and detecting orphans."""

from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.dto.admin_account import (
    AdminAccountPatternCreate,
    AdminAccountPatternListResponse,
    AdminAccountPatternResponse,
    ApplyAdminPatternsResponse,
    OrphanedAdminAccountsResponse,
    OrphanedAdminAccountWarning,
)
from licence_api.models.dto.license import LicenseResponse
from licence_api.models.orm.admin_account_pattern import AdminAccountPatternORM
from licence_api.repositories.admin_account_pattern_repository import (
    AdminAccountPatternRepository,
)
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.user_repository import UserRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType


class AdminAccountService:
    """Service for managing admin account patterns and orphan detection."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.pattern_repo = AdminAccountPatternRepository(session)
        self.license_repo = LicenseRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.user_repo = UserRepository(session)
        self.audit_service = AuditService(session)

    def _pattern_to_response(
        self,
        pattern: AdminAccountPatternORM,
        match_count: int = 0,
        owner_name: str | None = None,
        creator_name: str | None = None,
    ) -> AdminAccountPatternResponse:
        """Convert ORM pattern to response DTO."""
        return AdminAccountPatternResponse(
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

    async def get_all_patterns(self) -> AdminAccountPatternListResponse:
        """Get all admin account patterns with match counts.

        Returns:
            AdminAccountPatternListResponse with all patterns
        """
        patterns_with_counts = await self.pattern_repo.get_all_with_match_counts()

        items = []
        for pattern, match_count in patterns_with_counts:
            items.append(self._pattern_to_response(pattern, match_count))

        return AdminAccountPatternListResponse(
            items=items,
            total=len(items),
        )

    async def get_pattern_by_id(self, pattern_id: UUID) -> AdminAccountPatternResponse | None:
        """Get a single pattern by ID.

        Args:
            pattern_id: Pattern UUID

        Returns:
            AdminAccountPatternResponse or None if not found
        """
        pattern = await self.pattern_repo.get_by_id(pattern_id)
        if not pattern:
            return None

        match_count = await self.pattern_repo.get_match_count(pattern_id)
        return self._pattern_to_response(pattern, match_count)

    async def create_pattern(
        self,
        data: AdminAccountPatternCreate,
        created_by: UUID | None = None,
        request: Request | None = None,
    ) -> AdminAccountPatternResponse:
        """Create a new admin account pattern.

        Args:
            data: Pattern creation data
            created_by: Admin user ID who created the pattern
            request: HTTP request for audit logging

        Returns:
            Created AdminAccountPatternResponse
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
            action=AuditAction.ADMIN_ACCOUNT_PATTERN_CREATE,
            resource_type=ResourceType.ADMIN_ACCOUNT_PATTERN,
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
        """Delete an admin account pattern.

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
                action=AuditAction.ADMIN_ACCOUNT_PATTERN_DELETE,
                resource_type=ResourceType.ADMIN_ACCOUNT_PATTERN,
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
    ) -> ApplyAdminPatternsResponse:
        """Apply all patterns to all licenses.

        Marks matching licenses as admin accounts.

        Args:
            admin_user_id: Admin user applying patterns
            request: HTTP request for audit logging

        Returns:
            ApplyAdminPatternsResponse with count of updated licenses
        """
        patterns = await self.pattern_repo.get_all()
        updated_count = 0
        patterns_applied = 0

        for pattern in patterns:
            matching_licenses = await self.pattern_repo.find_matching_licenses(pattern)
            pattern_updates = 0

            for license in matching_licenses:
                # Only update if not already marked as admin account
                if not license.is_admin_account:
                    license.is_admin_account = True
                    license.admin_account_name = pattern.name
                    license.admin_account_owner_id = pattern.owner_id
                    updated_count += 1
                    pattern_updates += 1

            if pattern_updates > 0:
                patterns_applied += 1

        # Audit log the application
        if admin_user_id:
            await self.audit_service.log(
                action=AuditAction.ADMIN_ACCOUNT_PATTERNS_APPLY,
                resource_type=ResourceType.ADMIN_ACCOUNT_PATTERN,
                admin_user_id=admin_user_id,
                changes={
                    "updated_count": updated_count,
                    "patterns_applied": patterns_applied,
                },
                request=request,
            )

        await self.session.commit()

        return ApplyAdminPatternsResponse(
            updated_count=updated_count,
            patterns_applied=patterns_applied,
        )

    async def check_and_mark_license(
        self, license_external_user_id: str
    ) -> AdminAccountPatternORM | None:
        """Check if an email matches any pattern and return the matching pattern.

        This method is used during sync to automatically mark licenses as admin accounts.

        Args:
            license_external_user_id: The email address to check

        Returns:
            The matching pattern if found, None otherwise
        """
        return await self.pattern_repo.matches_email(license_external_user_id)

    async def get_orphaned_admin_accounts(self) -> OrphanedAdminAccountsResponse:
        """Get all admin accounts where the owner has been offboarded.

        Returns:
            OrphanedAdminAccountsResponse with list of warnings
        """
        # Use repository method instead of direct SQLAlchemy query (MVC-03 fix)
        rows = await self.license_repo.get_orphaned_admin_accounts()

        items = []
        for license_orm, employee_orm, provider_orm in rows:
            items.append(
                OrphanedAdminAccountWarning(
                    license_id=license_orm.id,
                    external_user_id=license_orm.external_user_id,
                    provider_id=provider_orm.id,
                    provider_name=provider_orm.display_name,
                    admin_account_name=license_orm.admin_account_name,
                    owner_id=employee_orm.id,
                    owner_name=employee_orm.full_name,
                    owner_email=employee_orm.email,
                    offboarded_at=employee_orm.offboarded_at,
                )
            )

        return OrphanedAdminAccountsResponse(
            items=items,
            total=len(items),
        )

    async def get_admin_account_licenses(
        self,
        search: str | None = None,
        provider_id: UUID | None = None,
        owner_id: UUID | None = None,
        include_orphaned_only: bool = False,
        sort_by: str = "external_user_id",
        sort_dir: str = "asc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[LicenseResponse], int]:
        """Get all licenses marked as admin accounts.

        Args:
            search: Search by email
            provider_id: Filter by provider
            owner_id: Filter by owner (employee ID)
            include_orphaned_only: Only include orphaned admin accounts
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
            admin_accounts_only=True,
            admin_account_owner_id=owner_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=offset,
            limit=page_size,
        )

        # Batch load all admin account owners to avoid N+1 queries
        admin_owner_ids = [
            license_orm.admin_account_owner_id
            for license_orm, _, _ in results
            if license_orm.admin_account_owner_id
        ]
        owners_map = {}
        if admin_owner_ids:
            owners = await self.employee_repo.get_by_ids(admin_owner_ids)
            owners_map = {emp.id: emp for emp in owners}

        items = []
        for license_orm, provider_orm, employee_orm in results:
            # Get admin account owner info from pre-loaded cache
            admin_account_owner_name = None
            admin_account_owner_status = None
            if license_orm.admin_account_owner_id:
                owner = owners_map.get(license_orm.admin_account_owner_id)
                if owner:
                    admin_account_owner_name = owner.full_name
                    admin_account_owner_status = owner.status

            # Filter orphaned only if requested
            if include_orphaned_only and admin_account_owner_status != "offboarded":
                continue

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
                    is_admin_account=license_orm.is_admin_account,
                    admin_account_name=license_orm.admin_account_name,
                    admin_account_owner_id=license_orm.admin_account_owner_id,
                    admin_account_owner_name=admin_account_owner_name,
                    admin_account_owner_status=admin_account_owner_status,
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
    ) -> AdminAccountPatternResponse | None:
        """Create a pattern from an exact email address.

        Used when marking a license as admin account with "apply_globally" option.
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
            data=AdminAccountPatternCreate(
                email_pattern=email,
                name=name,
                owner_id=owner_id,
                notes=notes,
            ),
            created_by=created_by,
        )
