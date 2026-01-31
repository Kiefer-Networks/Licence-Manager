"""License service for managing licenses."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from decimal import Decimal

from licence_api.models.dto.license import (
    LicenseResponse,
    LicenseListResponse,
    LicenseStats,
    CategorizedLicensesResponse,
)
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.utils.domain_check import is_company_email


class LicenseService:
    """Service for license management."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.license_repo = LicenseRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.settings_repo = SettingsRepository(session)

    async def _get_company_domains(self) -> list[str]:
        """Get company domains from settings."""
        setting = await self.settings_repo.get("company_domains")
        if setting is None:
            return []
        return setting.get("domains", [])

    def _check_external_email(
        self, external_user_id: str, company_domains: list[str]
    ) -> bool:
        """Check if an external_user_id (email) is external.

        Returns True if:
        - Company domains are configured AND
        - The external_user_id is an email AND
        - The email does NOT belong to company domains
        """
        if not company_domains:
            return False
        if "@" not in external_user_id:
            return False
        return not is_company_email(external_user_id, company_domains)

    def _get_display_name_from_pricing(
        self, license_type: str | None, provider_config: dict | None
    ) -> str | None:
        """Get the display name for a license type from provider pricing config."""
        if not license_type or not provider_config:
            return None
        license_pricing_config = provider_config.get("license_pricing", {})
        type_pricing = license_pricing_config.get(license_type, {})
        return type_pricing.get("display_name")

    async def list_licenses(
        self,
        provider_id: UUID | None = None,
        employee_id: UUID | None = None,
        status: str | None = None,
        unassigned_only: bool = False,
        external_only: bool = False,
        search: str | None = None,
        department: str | None = None,
        sort_by: str = "synced_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> LicenseListResponse:
        """List licenses with filtering and pagination.

        Args:
            provider_id: Filter by provider
            employee_id: Filter by employee
            status: Filter by status
            unassigned_only: Only return unassigned licenses
            external_only: Only return licenses with external emails
            search: Search by user email or external_user_id
            department: Filter by employee department
            sort_by: Column to sort by
            sort_dir: Sort direction (asc/desc)
            page: Page number (1-indexed)
            page_size: Page size

        Returns:
            LicenseListResponse with paginated results
        """
        # Load company domains for external email check
        company_domains = await self._get_company_domains() if external_only else None

        # Use SQL-based filtering for external emails (much faster than Python filtering)
        offset = (page - 1) * page_size
        results, total = await self.license_repo.get_all_with_details(
            provider_id=provider_id,
            employee_id=employee_id,
            status=status,
            unassigned_only=unassigned_only,
            search=search,
            department=department,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=offset,
            limit=page_size,
            external_only=external_only,
            company_domains=company_domains,
        )

        items = []
        for license_orm, provider_orm, employee_orm in results:
            # Get service account owner name if set
            service_account_owner_name = None
            if license_orm.is_service_account and license_orm.service_account_owner_id:
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
                    license_type_display_name=self._get_display_name_from_pricing(
                        license_orm.license_type, provider_orm.config
                    ),
                    status=license_orm.status,
                    assigned_at=license_orm.assigned_at,
                    last_activity_at=license_orm.last_activity_at,
                    monthly_cost=license_orm.monthly_cost,
                    currency=license_orm.currency,
                    metadata=license_orm.extra_data or {},
                    synced_at=license_orm.synced_at,
                    is_external_email=self._check_external_email(
                        license_orm.external_user_id, company_domains
                    ),
                    employee_status=employee_orm.status if employee_orm else None,
                    is_service_account=license_orm.is_service_account,
                    service_account_name=license_orm.service_account_name,
                    service_account_owner_id=license_orm.service_account_owner_id,
                    service_account_owner_name=service_account_owner_name,
                )
            )

        return LicenseListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_license(self, license_id: UUID) -> LicenseResponse | None:
        """Get a single license by ID.

        Args:
            license_id: License UUID

        Returns:
            LicenseResponse or None if not found
        """
        license_orm = await self.license_repo.get_by_id(license_id)
        if license_orm is None:
            return None

        # Get provider
        from licence_api.repositories.provider_repository import ProviderRepository
        provider_repo = ProviderRepository(self.session)
        provider_orm = await provider_repo.get_by_id(license_orm.provider_id)

        # Get employee if assigned
        employee_orm = None
        if license_orm.employee_id:
            employee_orm = await self.employee_repo.get_by_id(license_orm.employee_id)

        # Load company domains for external email check
        company_domains = await self._get_company_domains()

        # Get service account owner name if set
        service_account_owner_name = None
        if license_orm.is_service_account and license_orm.service_account_owner_id:
            owner = await self.employee_repo.get_by_id(license_orm.service_account_owner_id)
            service_account_owner_name = owner.full_name if owner else None

        # Get admin account owner info if set
        admin_account_owner_name = None
        admin_account_owner_status = None
        if license_orm.is_admin_account and license_orm.admin_account_owner_id:
            owner = await self.employee_repo.get_by_id(license_orm.admin_account_owner_id)
            if owner:
                admin_account_owner_name = owner.full_name
                admin_account_owner_status = owner.status

        return LicenseResponse(
            id=license_orm.id,
            provider_id=license_orm.provider_id,
            provider_name=provider_orm.display_name if provider_orm else "Unknown",
            employee_id=license_orm.employee_id,
            employee_email=employee_orm.email if employee_orm else None,
            employee_name=employee_orm.full_name if employee_orm else None,
            external_user_id=license_orm.external_user_id,
            license_type=license_orm.license_type,
            license_type_display_name=self._get_display_name_from_pricing(
                license_orm.license_type, provider_orm.config if provider_orm else None
            ),
            status=license_orm.status,
            assigned_at=license_orm.assigned_at,
            last_activity_at=license_orm.last_activity_at,
            monthly_cost=license_orm.monthly_cost,
            currency=license_orm.currency,
            metadata=license_orm.extra_data or {},
            synced_at=license_orm.synced_at,
            is_external_email=self._check_external_email(
                license_orm.external_user_id, company_domains
            ),
            employee_status=employee_orm.status if employee_orm else None,
            is_service_account=license_orm.is_service_account,
            service_account_name=license_orm.service_account_name,
            service_account_owner_id=license_orm.service_account_owner_id,
            service_account_owner_name=service_account_owner_name,
            is_admin_account=license_orm.is_admin_account,
            admin_account_name=license_orm.admin_account_name,
            admin_account_owner_id=license_orm.admin_account_owner_id,
            admin_account_owner_name=admin_account_owner_name,
            admin_account_owner_status=admin_account_owner_status,
        )

    async def get_employee_licenses(self, employee_id: UUID) -> list[LicenseResponse]:
        """Get all licenses for an employee.

        Args:
            employee_id: Employee UUID

        Returns:
            List of LicenseResponse
        """
        result = await self.list_licenses(employee_id=employee_id, page_size=1000)
        return result.items

    async def get_statistics(self) -> dict[str, Any]:
        """Get license statistics.

        Returns:
            Dict with statistics
        """
        return await self.license_repo.get_statistics()

    async def assign_license_to_employee(
        self,
        license_id: UUID,
        employee_id: UUID,
    ) -> LicenseResponse | None:
        """Manually assign a license to an employee.

        Args:
            license_id: License UUID
            employee_id: Employee UUID

        Returns:
            Updated LicenseResponse or None if not found
        """
        from datetime import datetime, timezone

        license_orm = await self.license_repo.update(
            license_id,
            employee_id=employee_id,
            assigned_at=datetime.now(timezone.utc),
        )

        if license_orm is None:
            return None

        return await self.get_license(license_id)

    async def unassign_license(self, license_id: UUID) -> LicenseResponse | None:
        """Unassign a license from employee.

        Args:
            license_id: License UUID

        Returns:
            Updated LicenseResponse or None if not found
        """
        license_orm = await self.license_repo.update(
            license_id,
            employee_id=None,
            assigned_at=None,
        )

        if license_orm is None:
            return None

        return await self.get_license(license_id)

    async def get_categorized_licenses(
        self,
        provider_id: UUID | None = None,
        sort_by: str = "external_user_id",
        sort_dir: str = "asc",
    ) -> CategorizedLicensesResponse:
        """Get licenses categorized by match status.

        Categories (in priority order):
        - Service Accounts: Licenses marked as service accounts
        - External Guest: Confirmed external guests
        - External Review: External emails needing review
        - Suggested: Licenses with suggested matches needing confirmation
        - Assigned: Confirmed/auto-matched internal licenses
        - Unassigned: Internal licenses without any match

        Args:
            provider_id: Optional provider filter
            sort_by: Column to sort by (default: external_user_id for alphabetical)
            sort_dir: Sort direction (default: asc for alphabetical)

        Returns:
            CategorizedLicensesResponse with all categories and stats
        """
        # Load company domains for external email check
        company_domains = await self._get_company_domains()

        # Fetch all licenses (we need all to categorize properly)
        results, _ = await self.license_repo.get_all_with_details(
            provider_id=provider_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=0,
            limit=10000,
        )

        assigned: list[LicenseResponse] = []
        unassigned: list[LicenseResponse] = []
        external: list[LicenseResponse] = []
        service_accounts: list[LicenseResponse] = []
        suggested: list[LicenseResponse] = []
        external_review: list[LicenseResponse] = []
        external_guest: list[LicenseResponse] = []

        # Stats tracking
        total_active = 0
        total_inactive = 0
        total_monthly_cost = Decimal("0")
        potential_savings = Decimal("0")
        currencies_found: set[str] = set()

        # Cache for employee names
        employee_cache: dict[UUID, tuple[str | None, str | None]] = {}

        async def get_employee_info(emp_id: UUID | None) -> tuple[str | None, str | None]:
            """Get employee name and email from cache or DB."""
            if emp_id is None:
                return None, None
            if emp_id not in employee_cache:
                emp = await self.employee_repo.get_by_id(emp_id)
                employee_cache[emp_id] = (emp.full_name, emp.email) if emp else (None, None)
            return employee_cache[emp_id]

        for license_orm, provider_orm, employee_orm in results:
            is_external = self._check_external_email(
                license_orm.external_user_id, company_domains
            )
            is_active = license_orm.status == "active"
            is_assigned = license_orm.employee_id is not None
            is_offboarded = employee_orm and employee_orm.status == "offboarded"
            is_service_account = license_orm.is_service_account
            match_status = license_orm.match_status
            has_suggestion = license_orm.suggested_employee_id is not None

            # Get service account owner name
            service_account_owner_name, _ = await get_employee_info(
                license_orm.service_account_owner_id if is_service_account else None
            )

            # Get suggested employee info
            suggested_name, suggested_email = await get_employee_info(
                license_orm.suggested_employee_id
            )

            license_response = LicenseResponse(
                id=license_orm.id,
                provider_id=license_orm.provider_id,
                provider_name=provider_orm.display_name,
                employee_id=license_orm.employee_id,
                employee_email=employee_orm.email if employee_orm else None,
                employee_name=employee_orm.full_name if employee_orm else None,
                external_user_id=license_orm.external_user_id,
                license_type=license_orm.license_type,
                license_type_display_name=self._get_display_name_from_pricing(
                    license_orm.license_type, provider_orm.config
                ),
                status=license_orm.status,
                assigned_at=license_orm.assigned_at,
                last_activity_at=license_orm.last_activity_at,
                monthly_cost=license_orm.monthly_cost,
                currency=license_orm.currency,
                metadata=license_orm.extra_data or {},
                synced_at=license_orm.synced_at,
                is_external_email=is_external,
                employee_status=employee_orm.status if employee_orm else None,
                is_service_account=is_service_account,
                service_account_name=license_orm.service_account_name,
                service_account_owner_id=license_orm.service_account_owner_id,
                service_account_owner_name=service_account_owner_name,
                # Match fields
                suggested_employee_id=license_orm.suggested_employee_id,
                suggested_employee_name=suggested_name,
                suggested_employee_email=suggested_email,
                match_confidence=license_orm.match_confidence,
                match_status=match_status,
                match_method=license_orm.match_method,
            )

            # Track active/inactive
            if is_active:
                total_active += 1
            else:
                total_inactive += 1

            # Track monthly cost (only active licenses)
            if is_active and license_orm.monthly_cost:
                total_monthly_cost += license_orm.monthly_cost
                currencies_found.add(license_orm.currency)

            # Track potential savings (unassigned + offboarded, only active)
            # Service accounts and confirmed external guests are intentional
            if is_active and license_orm.monthly_cost and not is_service_account:
                if match_status != "external_guest" and (not is_assigned or is_offboarded):
                    potential_savings += license_orm.monthly_cost

            # Categorize in priority order:
            # 1. Service accounts first (they are intentionally unlinked)
            # 2. External guest (confirmed external - no action needed)
            # 3. Suggested matches (any license with suggestion, needs review)
            # 4. External review (external email without suggestion, needs decision)
            # 5. Assigned (confirmed or auto-matched)
            # 6. Unassigned (internal, no match found)
            if is_service_account:
                service_accounts.append(license_response)
            elif match_status == "external_guest":
                external_guest.append(license_response)
            elif has_suggestion:
                # Any license with a suggested match goes here (internal or external)
                suggested.append(license_response)
            elif match_status == "external_review" or (is_external and not is_assigned):
                # External emails without suggestions need review
                external_review.append(license_response)
            elif is_assigned:
                assigned.append(license_response)
            else:
                unassigned.append(license_response)

        # For backward compatibility, also populate the external list
        # with all external licenses (both review and confirmed guest)
        external = external_review + external_guest

        currencies_list = sorted(currencies_found) if currencies_found else ["EUR"]
        has_currency_mix = len(currencies_found) > 1

        stats = LicenseStats(
            total_active=total_active,
            total_assigned=len(assigned),
            total_unassigned=len(unassigned),
            total_inactive=total_inactive,
            total_external=len(external),
            total_service_accounts=len(service_accounts),
            total_suggested=len(suggested),
            total_external_review=len(external_review),
            total_external_guest=len(external_guest),
            monthly_cost=total_monthly_cost,
            potential_savings=potential_savings,
            currency=currencies_list[0] if len(currencies_list) == 1 else "EUR",
            has_currency_mix=has_currency_mix,
            currencies_found=currencies_list,
        )

        return CategorizedLicensesResponse(
            assigned=assigned,
            unassigned=unassigned,
            external=external,
            service_accounts=service_accounts,
            suggested=suggested,
            external_review=external_review,
            external_guest=external_guest,
            stats=stats,
        )

    async def update_service_account_status(
        self,
        license_id: UUID,
        is_service_account: bool,
        service_account_name: str | None = None,
        service_account_owner_id: UUID | None = None,
    ) -> tuple[dict, dict] | None:
        """Update service account status for a license.

        Args:
            license_id: License UUID
            is_service_account: Whether this is a service account
            service_account_name: Name of the service account
            service_account_owner_id: Owner employee ID

        Returns:
            Tuple of (old_values, new_values) for audit logging, or None if not found
        """
        license_orm = await self.license_repo.get_by_id(license_id)
        if license_orm is None:
            return None

        # Store old values for audit
        old_values = {
            "is_service_account": license_orm.is_service_account,
            "service_account_name": license_orm.service_account_name,
            "service_account_owner_id": str(license_orm.service_account_owner_id) if license_orm.service_account_owner_id else None,
        }

        # Update service account fields
        license_orm.is_service_account = is_service_account
        license_orm.service_account_name = service_account_name if is_service_account else None
        license_orm.service_account_owner_id = service_account_owner_id if is_service_account else None

        # If marking as service account, clear the employee assignment
        if is_service_account and license_orm.employee_id:
            license_orm.employee_id = None

        await self.session.flush()

        new_values = {
            "is_service_account": is_service_account,
            "service_account_name": service_account_name,
            "service_account_owner_id": str(service_account_owner_id) if service_account_owner_id else None,
        }

        return old_values, new_values

    async def update_admin_account_status(
        self,
        license_id: UUID,
        is_admin_account: bool,
        admin_account_name: str | None = None,
        admin_account_owner_id: UUID | None = None,
    ) -> tuple[dict, dict] | None:
        """Update admin account status for a license.

        Args:
            license_id: License UUID
            is_admin_account: Whether this is an admin account
            admin_account_name: Name of the admin account
            admin_account_owner_id: Owner employee ID

        Returns:
            Tuple of (old_values, new_values) for audit logging, or None if not found
        """
        license_orm = await self.license_repo.get_by_id(license_id)
        if license_orm is None:
            return None

        # Store old values for audit
        old_values = {
            "is_admin_account": license_orm.is_admin_account,
            "admin_account_name": license_orm.admin_account_name,
            "admin_account_owner_id": str(license_orm.admin_account_owner_id) if license_orm.admin_account_owner_id else None,
        }

        # Update admin account fields
        license_orm.is_admin_account = is_admin_account
        license_orm.admin_account_name = admin_account_name if is_admin_account else None
        license_orm.admin_account_owner_id = admin_account_owner_id if is_admin_account else None

        await self.session.flush()

        new_values = {
            "is_admin_account": is_admin_account,
            "admin_account_name": admin_account_name,
            "admin_account_owner_id": str(admin_account_owner_id) if admin_account_owner_id else None,
        }

        return old_values, new_values

    async def get_license_external_user_id(self, license_id: UUID) -> str | None:
        """Get the external_user_id for a license.

        Args:
            license_id: License UUID

        Returns:
            External user ID or None if not found
        """
        license_orm = await self.license_repo.get_by_id(license_id)
        return license_orm.external_user_id if license_orm else None
