"""Report service for generating license reports.

Architecture Note (MVC-04):
    This service performs complex reporting and analytics operations that involve
    specialized aggregations, multi-table joins, and business-specific calculations.
    All database access is delegated to the appropriate repositories
    (LicenseRepository, EmployeeRepository, ProviderRepository, etc.).
    The service layer focuses on business logic, data transformation, and
    report composition.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.dto.dashboard import (
    DashboardResponse,
    ProviderSummary,
    RecentOffboarding,
    UnassignedLicense,
)
from licence_api.models.dto.report import (
    CancelledLicense,
    CancelledLicensesReport,
    CostReportResponse,
    CostsByDepartmentReport,
    CostsByEmployeeReport,
    CostTrendEntry,
    CostTrendReport,
    DepartmentCost,
    DuplicateAccount,
    DuplicateAccountsReport,
    EmployeeCost,
    EmployeeLicense,
    ExpiringContract,
    ExpiringContractsReport,
    ExpiringLicense,
    ExpiringLicensesReport,
    ExternalUserLicense,
    ExternalUsersReport,
    InactiveLicenseEntry,
    InactiveLicenseReport,
    LicenseLifecycleOverview,
    LicenseRecommendation,
    LicenseRecommendationsReport,
    MonthlyCost,
    OffboardedEmployee,
    OffboardingReport,
    ProviderUtilization,
    UtilizationReport,
)
from licence_api.repositories.cost_snapshot_repository import CostSnapshotRepository
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_package_repository import LicensePackageRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.repositories.user_repository import UserRepository
from licence_api.services.expiration_service import ExpirationService
from licence_api.utils.domain_check import is_company_email


class ReportService:
    """Service for generating reports."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.license_repo = LicenseRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.settings_repo = SettingsRepository(session)
        self.snapshot_repo = CostSnapshotRepository(session)
        self.package_repo = LicensePackageRepository(session)
        self.user_repo = UserRepository(session)
        self.expiration_service = ExpirationService(session)

    async def get_dashboard_cached(self, department: str | None = None) -> DashboardResponse:
        """Get dashboard data with cache layer.

        Checks cache first, falls back to database and caches the result.

        Args:
            department: Optional department filter

        Returns:
            DashboardResponse with all dashboard metrics
        """
        from licence_api.services.cache_service import get_cache_service

        cache = await get_cache_service()
        cached = await cache.get_dashboard(department=department)
        if cached:
            return DashboardResponse(**cached)

        result = await self.get_dashboard(department=department)

        await cache.set_dashboard(result, department=department)
        return result

    async def get_utilization_report_cached(self) -> "UtilizationReport":
        """Get utilization report with cache layer.

        Returns:
            UtilizationReport
        """
        from licence_api.services.cache_service import get_cache_service

        cache = await get_cache_service()
        cached = await cache.get_report("utilization")
        if cached:
            return UtilizationReport(**cached)

        result = await self.get_utilization_report()
        await cache.set_report("utilization", result)
        return result

    async def get_duplicate_accounts_cached(self) -> "DuplicateAccountsReport":
        """Get duplicate accounts report with cache layer.

        Returns:
            DuplicateAccountsReport
        """
        from licence_api.services.cache_service import get_cache_service

        cache = await get_cache_service()
        cached = await cache.get_report("duplicate_accounts")
        if cached:
            return DuplicateAccountsReport(**cached)

        result = await self.get_duplicate_accounts()
        await cache.set_report("duplicate_accounts", result)
        return result

    async def get_costs_by_department_cached(self) -> "CostsByDepartmentReport":
        """Get costs by department report with cache layer.

        Returns:
            CostsByDepartmentReport
        """
        from licence_api.services.cache_service import get_cache_service

        cache = await get_cache_service()
        cached = await cache.get_report("costs_by_department")
        if cached:
            return CostsByDepartmentReport(**cached)

        result = await self.get_costs_by_department()
        await cache.set_report("costs_by_department", result)
        return result

    async def get_dashboard(self, department: str | None = None) -> DashboardResponse:
        """Get dashboard data.

        Args:
            department: Optional department filter

        Returns:
            DashboardResponse with all dashboard metrics
        """
        # Employee stats
        employee_stats = await self.employee_repo.count_by_status(department=department)
        total_employees = sum(employee_stats.values())
        active_employees = employee_stats.get("active", 0)
        offboarded_employees = employee_stats.get("offboarded", 0)

        # License stats
        license_stats = await self.license_repo.get_statistics(department=department)

        # Provider summaries
        providers_with_counts = await self.provider_repo.get_all_with_license_counts()
        provider_summaries = []
        for provider, count in providers_with_counts:
            provider_summaries.append(
                ProviderSummary(
                    id=str(provider.id),
                    name=provider.name,
                    display_name=provider.display_name,
                    total_licenses=count,
                    active_licenses=count,  # Simplified
                    inactive_licenses=0,
                    last_sync_at=provider.last_sync_at,
                )
            )

        # Recent offboardings - using batch query to avoid N+1
        recent_offboarded = await self.employee_repo.get_recently_offboarded(
            days=30, department=department
        )
        recent_offboardings = []
        if recent_offboarded:
            # Batch fetch all licenses with providers for offboarded employees
            employee_ids = [emp.id for emp in recent_offboarded]
            employee_licenses = await self.license_repo.get_licenses_with_providers_for_employees(
                employee_ids
            )

            for employee in recent_offboarded:
                licenses_with_providers = employee_licenses.get(employee.id, [])
                if licenses_with_providers:
                    # Get unique provider names from the batch result
                    provider_names = list(
                        {provider.display_name for _, provider in licenses_with_providers}
                    )

                    recent_offboardings.append(
                        RecentOffboarding(
                            employee_id=str(employee.id),
                            employee_name=employee.full_name,
                            employee_email=employee.email,
                            termination_date=datetime.combine(
                                employee.termination_date, datetime.min.time()
                            )
                            if employee.termination_date
                            else None,
                            pending_licenses=len(licenses_with_providers),
                            provider_names=provider_names,
                        )
                    )

        # Unassigned licenses sample (only show if no department filter)
        unassigned_samples = []
        if not department:
            unassigned_results, _ = await self.license_repo.get_all_with_details(
                unassigned_only=True,
                limit=10,
            )
            unassigned_samples = [
                UnassignedLicense(
                    id=str(lic.id),
                    provider_name=provider.display_name,
                    provider_type=provider.name,
                    external_user_id=lic.external_user_id,
                    license_type=lic.license_type,
                    monthly_cost=lic.monthly_cost,
                )
                for lic, provider, _ in unassigned_results
            ]

        # Count external licenses using optimized SQL query
        external_count = 0
        setting = await self.settings_repo.get("company_domains")
        company_domains = setting.get("domains", []) if setting else []
        if company_domains:
            external_count = await self.license_repo.count_external_licenses(
                company_domains=company_domains,
                department=department,
                exclude_provider_name="hibob",
            )

        return DashboardResponse(
            total_employees=total_employees,
            active_employees=active_employees,
            offboarded_employees=offboarded_employees,
            total_licenses=license_stats["total"],
            active_licenses=license_stats["by_status"].get("active", 0),
            unassigned_licenses=license_stats["unassigned"],
            external_licenses=external_count,
            total_monthly_cost=license_stats["total_monthly_cost"],
            potential_savings=license_stats["potential_savings"],
            providers=provider_summaries,
            recent_offboardings=recent_offboardings,
            unassigned_license_samples=unassigned_samples,
        )

    async def get_cost_report(
        self,
        start_date: date,
        end_date: date,
        department: str | None = None,
    ) -> CostReportResponse:
        """Get cost report for date range.

        Args:
            start_date: Report start date
            end_date: Report end date
            department: Optional department filter

        Returns:
            CostReportResponse with cost breakdown
        """
        # Get all licenses with costs (exclude HRIS providers like hibob)
        # Don't filter by status - unassigned licenses still cost money
        results, _ = await self.license_repo.get_all_with_details(
            department=department,
            limit=10000,
        )

        # Group by provider and calculate costs
        provider_costs: dict[str, Decimal] = {}
        provider_counts: dict[str, int] = {}
        currencies_found: set[str] = set()

        for lic, provider, _ in results:
            # Skip HRIS providers (they don't have licenses)
            if provider.name == "hibob":
                continue
            name = provider.display_name
            cost = lic.monthly_cost or Decimal("0")
            provider_costs[name] = provider_costs.get(name, Decimal("0")) + cost
            provider_counts[name] = provider_counts.get(name, 0) + 1
            if cost > 0:
                currencies_found.add(lic.currency)

        # Create cost summary per provider (no month duplication)
        monthly_costs = []
        for provider_name in sorted(provider_costs.keys()):
            monthly_costs.append(
                MonthlyCost(
                    month=date.today().replace(day=1),
                    provider_name=provider_name,
                    cost=provider_costs[provider_name],
                    license_count=provider_counts.get(provider_name, 0),
                )
            )

        total_cost = sum(provider_costs.values())
        currencies_list = sorted(currencies_found) if currencies_found else ["EUR"]
        has_currency_mix = len(currencies_found) > 1

        return CostReportResponse(
            start_date=start_date,
            end_date=end_date,
            total_cost=total_cost,
            currency=currencies_list[0] if len(currencies_list) == 1 else "EUR",
            monthly_costs=monthly_costs,
            has_currency_mix=has_currency_mix,
            currencies_found=currencies_list,
        )

    async def get_inactive_license_report(
        self,
        days_threshold: int = 30,
        department: str | None = None,
    ) -> InactiveLicenseReport:
        """Get report of inactive licenses.

        Args:
            days_threshold: Days without activity to consider inactive
            department: Optional department filter

        Returns:
            InactiveLicenseReport
        """
        inactive = await self.license_repo.get_inactive(
            days_threshold=days_threshold,
            department=department,
            limit=100,
        )

        # Get company domains for external email detection
        setting = await self.settings_repo.get("company_domains")
        company_domains = setting.get("domains", []) if setting else []

        entries = []
        potential_savings = Decimal("0")

        for lic, provider, employee in inactive:
            days_inactive = 0
            if lic.last_activity_at:
                days_inactive = (datetime.now(UTC) - lic.last_activity_at).days
            else:
                days_inactive = days_threshold + 30  # Assume inactive since forever

            # Check if external email
            is_external = False
            if "@" in lic.external_user_id and company_domains:
                is_external = not is_company_email(lic.external_user_id, company_domains)

            entries.append(
                InactiveLicenseEntry(
                    license_id=str(lic.id),
                    provider_id=str(provider.id),
                    provider_name=provider.display_name,
                    employee_id=str(employee.id) if employee else None,
                    employee_name=employee.full_name if employee else None,
                    employee_email=employee.email if employee else None,
                    employee_status=employee.status if employee else None,
                    external_user_id=lic.external_user_id,
                    last_activity_at=lic.last_activity_at,
                    days_inactive=days_inactive,
                    monthly_cost=lic.monthly_cost,
                    is_external_email=is_external,
                )
            )

            if lic.monthly_cost:
                potential_savings += lic.monthly_cost

        return InactiveLicenseReport(
            threshold_days=days_threshold,
            total_inactive=len(entries),
            potential_savings=potential_savings,
            licenses=entries,
        )

    async def get_offboarding_report(
        self,
        department: str | None = None,
    ) -> OffboardingReport:
        """Get report of offboarded employees with pending licenses.

        Args:
            department: Optional department filter

        Returns:
            OffboardingReport
        """
        offboarded = await self.employee_repo.get_recently_offboarded(
            days=90, department=department, limit=50
        )
        employees_with_licenses = []

        if offboarded:
            # Batch fetch all licenses with providers to avoid N+1 queries
            employee_ids = [emp.id for emp in offboarded]
            employee_licenses = await self.license_repo.get_licenses_with_providers_for_employees(
                employee_ids
            )

            for employee in offboarded:
                licenses_with_providers = employee_licenses.get(employee.id, [])
                if licenses_with_providers:
                    pending_licenses = []
                    for lic, provider in licenses_with_providers:
                        pending_licenses.append(
                            {
                                "provider": provider.display_name,
                                "type": lic.license_type or "Unknown",
                                "external_id": lic.external_user_id,
                            }
                        )

                    days_since = 0
                    if employee.termination_date:
                        days_since = (date.today() - employee.termination_date).days

                    employees_with_licenses.append(
                        OffboardedEmployee(
                            employee_name=employee.full_name,
                            employee_email=employee.email,
                            termination_date=employee.termination_date,
                            days_since_offboarding=days_since,
                            pending_licenses=pending_licenses,
                        )
                    )

        return OffboardingReport(
            total_offboarded_with_licenses=len(employees_with_licenses),
            employees=employees_with_licenses,
        )

    async def get_external_users_report(
        self,
        department: str | None = None,
    ) -> ExternalUsersReport:
        """Get report of licenses with external (non-company) email addresses.

        Args:
            department: Optional department filter

        Returns:
            ExternalUsersReport
        """
        # Get company domains from settings
        setting = await self.settings_repo.get("company_domains")
        if setting is None:
            company_domains = []
        else:
            company_domains = setting.get("domains", [])

        # If no company domains configured, return empty report
        if not company_domains:
            return ExternalUsersReport(
                total_external=0,
                licenses=[],
            )

        # Get all licenses
        results, _ = await self.license_repo.get_all_with_details(
            department=department,
            limit=10000,
        )

        external_licenses = []
        for lic, provider, employee in results:
            # Skip if not an email address
            if "@" not in lic.external_user_id:
                continue

            # Skip HRIS providers
            if provider.name == "hibob":
                continue

            # Check if external
            if not is_company_email(lic.external_user_id, company_domains):
                external_licenses.append(
                    ExternalUserLicense(
                        license_id=str(lic.id),
                        provider_id=str(provider.id),
                        provider_name=provider.display_name,
                        external_user_id=lic.external_user_id,
                        employee_id=str(employee.id) if employee else None,
                        employee_name=employee.full_name if employee else None,
                        employee_email=employee.email if employee else None,
                        employee_status=employee.status if employee else None,
                        license_type=lic.license_type,
                        monthly_cost=lic.monthly_cost,
                    )
                )

        return ExternalUsersReport(
            total_external=len(external_licenses),
            licenses=external_licenses,
        )

    # ==================== QUICK WINS ====================

    async def get_expiring_contracts(
        self,
        days_ahead: int = 90,
    ) -> ExpiringContractsReport:
        """Get contracts expiring within specified days.

        Args:
            days_ahead: Number of days to look ahead (default 90)

        Returns:
            ExpiringContractsReport
        """
        cutoff_date = date.today() + timedelta(days=days_ahead)
        packages = await self.package_repo.get_expiring_contracts(
            cutoff_date=cutoff_date,
            today=date.today(),
        )

        contracts = []
        for pkg in packages:
            days_until = (pkg.contract_end - date.today()).days if pkg.contract_end else 0
            total_cost = None
            if pkg.cost_per_seat and pkg.total_seats:
                total_cost = pkg.cost_per_seat * pkg.total_seats

            contracts.append(
                ExpiringContract(
                    package_id=str(pkg.id),
                    provider_id=str(pkg.provider_id),
                    provider_name=pkg.provider.display_name if pkg.provider else "Unknown",
                    license_type=pkg.license_type,
                    display_name=pkg.display_name,
                    total_seats=pkg.total_seats,
                    contract_end=pkg.contract_end,
                    days_until_expiry=days_until,
                    auto_renew=pkg.auto_renew,
                    total_cost=total_cost,
                    currency=pkg.currency,
                )
            )

        return ExpiringContractsReport(
            total_expiring=len(contracts),
            contracts=contracts,
        )

    async def get_utilization_report(self) -> UtilizationReport:
        """Get comprehensive license utilization report.

        Shows for each provider:
        - Purchased seats (from packages or license_info)
        - Active licenses (all with status=active)
        - Assigned licenses (with employee_id)
        - Unassigned licenses (without employee_id)
        - External licenses (external email addresses)
        - Costs and waste calculations

        Returns:
            UtilizationReport
        """
        from licence_api.models.orm.license_package import LicensePackageORM

        # Get company domains for external email detection
        company_domains: list[str] = []
        domains_setting = await self.settings_repo.get("company_domains")
        if domains_setting:
            company_domains = domains_setting.get("domains", [])

        # Get all enabled providers (except hibob)
        enabled_providers = await self.provider_repo.get_enabled_excluding("hibob")
        all_providers = {p.id: p for p in enabled_providers}

        # Get manual packages
        all_packages = await self.package_repo.get_all_with_providers()
        packages_by_provider: dict[str, list[LicensePackageORM]] = {}
        for pkg in all_packages:
            pid = str(pkg.provider_id)
            if pid not in packages_by_provider:
                packages_by_provider[pid] = []
            packages_by_provider[pid].append(pkg)

        # Get detailed license stats per provider via repository
        provider_stats = await self.license_repo.get_utilization_stats()

        # Count external licenses and their costs per provider
        external_by_provider: dict[str, dict] = {}
        if company_domains:
            for provider_id in all_providers.keys():
                ext_data = await self.license_repo.count_external_by_provider(
                    provider_id=provider_id,
                    company_domains=company_domains,
                )
                external_by_provider[str(provider_id)] = ext_data

        # Build report
        providers_list = []
        total_purchased = 0
        total_active = 0
        total_assigned = 0
        total_unassigned = 0
        total_external = 0
        total_monthly_cost = Decimal("0")
        total_external_cost = Decimal("0")
        total_monthly_waste = Decimal("0")

        for provider_id, provider in all_providers.items():
            pid = str(provider_id)
            stats = provider_stats.get(
                pid, {"active": 0, "assigned": 0, "unassigned": 0, "total_cost": Decimal("0")}
            )

            active = stats["active"]
            assigned = stats["assigned"]
            unassigned = stats["unassigned"]
            ext_data = external_by_provider.get(pid, {"count": 0, "cost": Decimal("0")})
            external = ext_data["count"]
            external_cost_from_db = ext_data["cost"]
            monthly_cost = stats["total_cost"]

            # Get purchased seats from packages or license_info
            purchased = 0
            cost_per_seat = None
            currency = "EUR"
            license_type = None

            if pid in packages_by_provider:
                # Use manual packages
                for pkg in packages_by_provider[pid]:
                    purchased += pkg.total_seats
                    if pkg.cost_per_seat:
                        cost_per_seat = pkg.cost_per_seat
                        if pkg.billing_cycle == "yearly":
                            cost_per_seat = cost_per_seat / 12
                        elif pkg.billing_cycle == "quarterly":
                            cost_per_seat = cost_per_seat / 3
                    currency = pkg.currency
                    license_type = pkg.display_name or pkg.license_type
            else:
                # Fallback to provider_license_info
                config = provider.config or {}
                license_info = config.get("provider_license_info", {})
                package_pricing = config.get("package_pricing", {})

                max_users = license_info.get("max_users")
                if max_users:
                    purchased = int(max_users)
                    license_type = (
                        license_info.get("sku_name", "").replace("_", " ").title() or None
                    )

                # Get cost from package_pricing
                if package_pricing.get("cost"):
                    try:
                        pkg_cost = Decimal(str(package_pricing["cost"]))
                        billing_cycle = package_pricing.get("billing_cycle", "yearly")
                        if billing_cycle == "yearly":
                            pkg_cost = pkg_cost / 12
                        elif billing_cycle == "quarterly":
                            pkg_cost = pkg_cost / 3
                        if purchased > 0:
                            cost_per_seat = pkg_cost / purchased
                        currency = package_pricing.get("currency", "EUR")
                    except (ValueError, TypeError):
                        pass

            # Calculate utilization (assigned / active is most meaningful)
            if active > 0:
                utilization = assigned / active * 100
            else:
                utilization = 0

            # Calculate provider monthly cost from package_pricing if not from licenses
            provider_monthly_cost = monthly_cost
            if not provider_monthly_cost and cost_per_seat and purchased > 0:
                provider_monthly_cost = cost_per_seat * purchased

            # Calculate waste (unassigned seats cost) - round to 2 decimals
            monthly_waste = None
            if cost_per_seat and unassigned > 0:
                monthly_waste = round(cost_per_seat * unassigned, 2)
                total_monthly_waste += monthly_waste

            # Calculate external cost - use DB cost if available, else estimate from cost_per_seat
            external_cost = None
            if external_cost_from_db and external_cost_from_db > 0:
                external_cost = round(external_cost_from_db, 2)
            elif cost_per_seat and external > 0:
                external_cost = round(cost_per_seat * external, 2)
            if external_cost:
                total_external_cost += external_cost

            # Add to totals
            total_purchased += purchased
            total_active += active
            total_assigned += assigned
            total_unassigned += unassigned
            total_external += external
            if provider_monthly_cost:
                total_monthly_cost += provider_monthly_cost

            # Only add providers with licenses or packages
            if active > 0 or purchased > 0:
                providers_list.append(
                    ProviderUtilization(
                        provider_id=pid,
                        provider_name=provider.display_name,
                        license_type=license_type,
                        purchased_seats=purchased,
                        active_seats=active,
                        assigned_seats=assigned,
                        unassigned_seats=unassigned,
                        external_seats=external,
                        utilization_percent=round(utilization, 1),
                        monthly_cost=round(provider_monthly_cost, 2)
                        if provider_monthly_cost
                        else None,
                        monthly_waste=monthly_waste,
                        external_cost=external_cost,
                        currency=currency,
                    )
                )

        # Sort by active seats descending
        providers_list.sort(key=lambda p: p.active_seats, reverse=True)

        # Calculate overall utilization (assigned / active)
        if total_active > 0:
            overall_util = total_assigned / total_active * 100
        else:
            overall_util = 0

        return UtilizationReport(
            total_purchased=total_purchased,
            total_active=total_active,
            total_assigned=total_assigned,
            total_unassigned=total_unassigned,
            total_external=total_external,
            overall_utilization=round(overall_util, 1),
            total_monthly_cost=round(total_monthly_cost, 2),
            total_monthly_waste=round(total_monthly_waste, 2),
            total_external_cost=round(total_external_cost, 2),
            providers=providers_list,
        )

    async def get_cost_trend(self, months: int = 6) -> CostTrendReport:
        """Get cost trend over the last N months.

        Uses historical snapshots when available, falls back to current
        data when no snapshots exist.

        Args:
            months: Number of months to show (default 6)

        Returns:
            CostTrendReport
        """
        # Try to get historical snapshots first
        snapshots = await self.snapshot_repo.get_trend(months=months, provider_id=None)

        trend_entries = []

        has_data = bool(snapshots)

        if snapshots:
            # Use real historical data
            for snapshot in snapshots:
                trend_entries.append(
                    CostTrendEntry(
                        month=snapshot.snapshot_date,
                        total_cost=snapshot.total_cost,
                        license_count=snapshot.license_count,
                    )
                )
        # No else: When no snapshots exist, we return empty months with has_data=False
        # instead of generating misleading synthetic data

        # Calculate trend direction
        if len(trend_entries) >= 2:
            first_cost = trend_entries[0].total_cost
            last_cost = trend_entries[-1].total_cost
            if first_cost > 0:
                percent_change = float((last_cost - first_cost) / first_cost * 100)
            else:
                percent_change = 0.0

            if percent_change > 5:
                direction = "up"
            elif percent_change < -5:
                direction = "down"
            else:
                direction = "stable"
        else:
            direction = "stable"
            percent_change = 0.0

        return CostTrendReport(
            months=trend_entries,
            trend_direction=direction,
            percent_change=round(percent_change, 1),
            has_data=has_data,
        )

    async def get_duplicate_accounts(self) -> DuplicateAccountsReport:
        """Find potential duplicate accounts across providers.

        Identifies licenses with the same email but different display names,
        which could indicate duplicate accounts or inconsistent naming.

        Returns:
            DuplicateAccountsReport
        """

        # Get all licenses with email addresses
        results, _ = await self.license_repo.get_all_with_details(limit=10000)

        # Group by email (case-insensitive)
        email_map: dict[str, list[tuple]] = {}
        for lic, provider, employee in results:
            if provider.name == "hibob":
                continue

            email = lic.external_user_id.lower().strip()
            if "@" not in email:
                continue

            # Get display name from extra_data (stored as "metadata" column) or external_user_id
            name = ""
            if lic.extra_data and isinstance(lic.extra_data, dict):
                name = lic.extra_data.get("name", "") or lic.extra_data.get("display_name", "")
            if not name:
                name = lic.external_user_id

            if email not in email_map:
                email_map[email] = []
            email_map[email].append((lic, provider, name))

        # Find duplicates (same email in multiple providers)
        duplicates = []
        total_savings = Decimal("0")

        for email, entries in email_map.items():
            if len(entries) > 1:
                # Check if it's actually a duplicate (same person, multiple providers is OK)
                # Flag as duplicate if same provider has multiple entries
                providers_seen: dict[str, int] = {}
                for _, provider, _ in entries:
                    providers_seen[provider.display_name] = (
                        providers_seen.get(provider.display_name, 0) + 1
                    )

                # Only flag if same provider appears multiple times
                has_true_duplicate = any(count > 1 for count in providers_seen.values())

                if has_true_duplicate:
                    providers = list(set(p.display_name for _, p, _ in entries))
                    names = list(set(n for _, _, n in entries if n))
                    license_ids = [str(lic.id) for lic, _, _ in entries]

                    total_cost = Decimal("0")
                    costs: list[Decimal] = []
                    for lic, _, _ in entries:
                        if lic.monthly_cost:
                            total_cost += lic.monthly_cost
                            costs.append(lic.monthly_cost)

                    # Savings = cost of removing duplicates (keep most expensive)
                    # Sort descending and sum all but the highest cost license
                    if len(costs) > 1:
                        costs_sorted = sorted(costs, reverse=True)
                        savings = sum(costs_sorted[1:], Decimal("0"))
                        total_savings += savings

                    duplicates.append(
                        DuplicateAccount(
                            email=email,
                            occurrences=len(entries),
                            providers=providers,
                            names=names,
                            license_ids=license_ids,
                            total_monthly_cost=total_cost,
                        )
                    )

        # Sort by occurrences descending
        duplicates.sort(key=lambda x: x.occurrences, reverse=True)

        return DuplicateAccountsReport(
            total_duplicates=len(duplicates),
            potential_savings=total_savings,
            duplicates=duplicates,
        )

    # ==================== COST BREAKDOWN REPORTS ====================

    async def get_costs_by_department(self) -> CostsByDepartmentReport:
        """Get license costs grouped by department.

        Returns:
            CostsByDepartmentReport with cost breakdown per department
        """
        from collections import defaultdict

        # Get all licenses with employee info
        results, _ = await self.license_repo.get_all_with_details(limit=10000)

        # Group by department
        dept_data: dict[str, dict] = defaultdict(
            lambda: {
                "employees": set(),
                "licenses": 0,
                "cost": Decimal("0"),
                "providers": defaultdict(lambda: Decimal("0")),
            }
        )

        for lic, provider, employee in results:
            if provider.name == "hibob":
                continue
            if lic.status != "active":
                continue

            # Determine department
            dept = "Unassigned"
            if employee:
                dept = employee.department or "No Department"
                dept_data[dept]["employees"].add(employee.id)

            dept_data[dept]["licenses"] += 1
            if lic.monthly_cost:
                dept_data[dept]["cost"] += lic.monthly_cost
                dept_data[dept]["providers"][provider.display_name] += lic.monthly_cost

        # Build response
        departments = []
        total_cost = Decimal("0")
        total_employees = 0

        for dept_name, data in dept_data.items():
            emp_count = len(data["employees"]) if dept_name != "Unassigned" else 0
            cost = data["cost"]
            cost_per_emp = cost / emp_count if emp_count > 0 else Decimal("0")

            # Top 3 providers by cost
            sorted_providers = sorted(data["providers"].items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            top_providers = [p[0] for p in sorted_providers]

            departments.append(
                DepartmentCost(
                    department=dept_name,
                    employee_count=emp_count,
                    license_count=data["licenses"],
                    total_monthly_cost=round(cost, 2),
                    cost_per_employee=round(cost_per_emp, 2),
                    top_providers=top_providers,
                )
            )

            total_cost += cost
            total_employees += emp_count

        # Sort by cost descending
        departments.sort(key=lambda x: x.total_monthly_cost, reverse=True)

        avg_cost = total_cost / total_employees if total_employees > 0 else Decimal("0")

        return CostsByDepartmentReport(
            total_departments=len(departments),
            total_monthly_cost=round(total_cost, 2),
            average_cost_per_employee=round(avg_cost, 2),
            departments=departments,
        )

    async def get_costs_by_employee(
        self,
        department: str | None = None,
        min_cost: float | None = None,
        limit: int = 100,
    ) -> CostsByEmployeeReport:
        """Get license costs grouped by employee.

        Args:
            department: Optional filter by department
            min_cost: Optional minimum monthly cost filter
            limit: Max employees to return (default 100, sorted by cost desc)

        Returns:
            CostsByEmployeeReport with cost breakdown per employee
        """
        import statistics

        # Get all licenses with employee info
        results, _ = await self.license_repo.get_all_with_details(
            department=department,
            limit=10000,
        )

        # Group by employee
        emp_data: dict[str, dict] = {}

        for lic, provider, employee in results:
            if provider.name == "hibob":
                continue
            if lic.status != "active":
                continue
            if not employee:
                continue  # Skip unassigned licenses

            emp_id = str(employee.id)
            if emp_id not in emp_data:
                emp_data[emp_id] = {
                    "employee": employee,
                    "licenses": [],
                    "cost": Decimal("0"),
                }

            cost = lic.monthly_cost or Decimal("0")
            emp_data[emp_id]["licenses"].append(
                EmployeeLicense(
                    provider_name=provider.display_name,
                    license_type=lic.license_type,
                    monthly_cost=cost if cost > 0 else None,
                )
            )
            emp_data[emp_id]["cost"] += cost

        # Build response
        employees = []
        costs_list = []

        for emp_id, data in emp_data.items():
            emp = data["employee"]
            cost = data["cost"]

            # Apply min_cost filter
            if min_cost is not None and float(cost) < min_cost:
                continue

            costs_list.append(float(cost))

            employees.append(
                EmployeeCost(
                    employee_id=emp_id,
                    employee_name=emp.full_name,
                    employee_email=emp.email,
                    department=emp.department,
                    status=emp.status,
                    license_count=len(data["licenses"]),
                    total_monthly_cost=round(cost, 2),
                    licenses=data["licenses"],
                )
            )

        # Sort by cost descending
        employees.sort(key=lambda x: x.total_monthly_cost, reverse=True)

        # Calculate statistics (based on filtered results)
        total_cost = sum(e.total_monthly_cost for e in employees)
        avg_cost = total_cost / len(employees) if employees else Decimal("0")
        median_cost = Decimal(str(statistics.median(costs_list))) if costs_list else Decimal("0")
        max_employee = employees[0].employee_name if employees else None

        # Limit results
        employees = employees[:limit]

        return CostsByEmployeeReport(
            total_employees=len(employees),
            total_monthly_cost=round(total_cost, 2),
            average_cost_per_employee=round(avg_cost, 2),
            median_cost_per_employee=round(median_cost, 2),
            max_cost_employee=max_employee,
            employees=employees,
        )

    # ==================== LICENSE LIFECYCLE REPORTS ====================

    async def get_expiring_licenses_report(
        self,
        days_ahead: int = 90,
    ) -> ExpiringLicensesReport:
        """Get report of licenses expiring within specified days.

        Args:
            days_ahead: Number of days to look ahead (default 90)

        Returns:
            ExpiringLicensesReport
        """
        expiring = await self.expiration_service.get_expiring_licenses(days_ahead=days_ahead)
        today = date.today()

        licenses = []
        expiring_30 = 0
        expiring_90 = 0
        needs_reorder_count = 0

        for lic, provider, employee in expiring:
            days_until = (lic.expires_at - today).days if lic.expires_at else 0

            if days_until <= 30:
                expiring_30 += 1
            if days_until <= 90:
                expiring_90 += 1
            if lic.needs_reorder:
                needs_reorder_count += 1

            licenses.append(
                ExpiringLicense(
                    license_id=lic.id,
                    provider_id=provider.id,
                    provider_name=provider.display_name,
                    external_user_id=lic.external_user_id,
                    license_type=lic.license_type,
                    employee_id=employee.id if employee else None,
                    employee_name=employee.full_name if employee else None,
                    expires_at=lic.expires_at,
                    days_until_expiry=days_until,
                    monthly_cost=lic.monthly_cost,
                    needs_reorder=lic.needs_reorder,
                    status=lic.status,
                )
            )

        return ExpiringLicensesReport(
            total_expiring=len(licenses),
            expiring_within_30_days=expiring_30,
            expiring_within_90_days=expiring_90,
            needs_reorder_count=needs_reorder_count,
            licenses=licenses,
        )

    async def get_cancelled_licenses_report(self) -> CancelledLicensesReport:
        """Get report of cancelled licenses.

        Returns:
            CancelledLicensesReport
        """
        cancelled = await self.expiration_service.get_cancelled_licenses()
        today = date.today()

        # Get canceller names via repository
        canceller_ids = [lic.cancelled_by for lic, _, _ in cancelled if lic.cancelled_by]
        canceller_names: dict = {}
        if canceller_ids:
            canceller_names = await self.user_repo.get_names_by_ids(canceller_ids)

        licenses = []
        pending_effective = 0
        already_effective = 0

        for lic, provider, employee in cancelled:
            is_effective = (
                lic.cancellation_effective_date and lic.cancellation_effective_date <= today
            )
            if is_effective:
                already_effective += 1
            else:
                pending_effective += 1

            licenses.append(
                CancelledLicense(
                    license_id=lic.id,
                    provider_id=provider.id,
                    provider_name=provider.display_name,
                    external_user_id=lic.external_user_id,
                    license_type=lic.license_type,
                    employee_id=employee.id if employee else None,
                    employee_name=employee.full_name if employee else None,
                    cancelled_at=lic.cancelled_at,
                    cancellation_effective_date=lic.cancellation_effective_date,
                    cancellation_reason=lic.cancellation_reason,
                    cancelled_by_name=canceller_names.get(lic.cancelled_by)
                    if lic.cancelled_by
                    else None,
                    monthly_cost=lic.monthly_cost,
                    is_effective=is_effective,
                )
            )

        return CancelledLicensesReport(
            total_cancelled=len(licenses),
            pending_effective=pending_effective,
            already_effective=already_effective,
            licenses=licenses,
        )

    async def get_license_lifecycle_overview(self) -> LicenseLifecycleOverview:
        """Get overall license lifecycle overview.

        Returns:
            LicenseLifecycleOverview
        """
        from licence_api.models.domain.license import LicenseStatus

        # Get counts by status via repository
        counts_by_status = await self.license_repo.count_by_status()

        # Count active licenses
        total_active = counts_by_status.get(LicenseStatus.ACTIVE, 0)
        total_expired = counts_by_status.get(LicenseStatus.EXPIRED, 0)

        # Count licenses needing reorder via repository
        total_needs_reorder = await self.license_repo.count_needs_reorder()

        # Get expiring licenses (within 90 days)
        expiring_report = await self.get_expiring_licenses_report(days_ahead=90)

        # Get cancelled licenses
        cancelled_report = await self.get_cancelled_licenses_report()

        return LicenseLifecycleOverview(
            total_active=total_active,
            total_expiring_soon=expiring_report.total_expiring,
            total_expired=total_expired,
            total_cancelled=cancelled_report.total_cancelled,
            total_needs_reorder=total_needs_reorder,
            expiring_licenses=expiring_report.licenses,
            cancelled_licenses=cancelled_report.licenses,
        )

    # ==================== LICENSE RECOMMENDATIONS ====================

    async def get_license_recommendations(
        self,
        min_days_inactive: int = 60,
        department: str | None = None,
        provider_id: str | None = None,
        limit: int = 100,
    ) -> LicenseRecommendationsReport:
        """Get license optimization recommendations based on usage patterns.

        Analyzes inactive licenses and generates actionable recommendations:
        - Cancel: For licenses inactive >90 days with no assigned employee
        - Reassign: For licenses inactive >60 days but assigned to active employee
        - Review: For other potentially wasteful licenses

        Args:
            min_days_inactive: Minimum days of inactivity to consider (default 60)
            department: Optional filter by department
            provider_id: Optional filter by provider
            limit: Maximum recommendations to return

        Returns:
            LicenseRecommendationsReport with prioritized recommendations
        """
        from uuid import UUID as PyUUID

        # Get company domains for external email detection
        setting = await self.settings_repo.get("company_domains")
        company_domains = setting.get("domains", []) if setting else []

        # Get inactive licenses
        provider_uuid = PyUUID(provider_id) if provider_id else None
        inactive = await self.license_repo.get_inactive(
            days_threshold=min_days_inactive,
            department=department,
            provider_id=provider_uuid,
            limit=limit * 2,  # Fetch more to account for filtering
        )

        recommendations: list[LicenseRecommendation] = []
        total_monthly_savings = Decimal("0")

        for lic, provider, employee in inactive:
            # Calculate days inactive
            days_inactive = 0
            if lic.last_activity_at:
                days_inactive = (datetime.now(UTC) - lic.last_activity_at).days
            else:
                days_inactive = min_days_inactive + 90  # Assume very inactive

            # Check if external email
            is_external = False
            if "@" in lic.external_user_id and company_domains:
                is_external = not is_company_email(lic.external_user_id, company_domains)

            # Determine recommendation type and priority
            monthly_cost = lic.monthly_cost or Decimal("0")
            yearly_savings = monthly_cost * 12

            # Priority calculation factors:
            # - Days inactive: more = higher priority
            # - Cost: higher cost = higher priority
            # - Employee status: offboarded = high priority
            # - External: external emails = higher priority

            recommendation_type = "review"
            recommendation_reason = ""
            priority = "low"

            if employee and employee.status == "offboarded":
                # Highest priority: offboarded employees with licenses
                recommendation_type = "cancel"
                recommendation_reason = "License assigned to offboarded employee"
                priority = "high"
            elif not employee and days_inactive > 90:
                # High priority: unassigned and very inactive
                recommendation_type = "cancel"
                recommendation_reason = f"Unassigned license inactive for {days_inactive} days"
                priority = "high"
            elif is_external and days_inactive > 60:
                # Medium-high priority: external email and inactive
                recommendation_type = "review"
                recommendation_reason = f"External email inactive for {days_inactive} days"
                priority = "high" if monthly_cost > 50 else "medium"
            elif employee and employee.status == "active" and days_inactive > 90:
                # Medium priority: active employee but very inactive license
                recommendation_type = "reassign"
                recommendation_reason = (
                    f"Active employee not using license for {days_inactive} days"
                )
                priority = "medium"
            elif days_inactive > 60:
                # Lower priority: moderately inactive
                recommendation_type = "review"
                recommendation_reason = f"License inactive for {days_inactive} days"
                priority = "low" if monthly_cost < 20 else "medium"
            else:
                # Skip if doesn't meet threshold
                continue

            # Boost priority for high-cost licenses
            if monthly_cost > 100 and priority == "medium":
                priority = "high"
            elif monthly_cost > 50 and priority == "low":
                priority = "medium"

            total_monthly_savings += monthly_cost

            recommendations.append(
                LicenseRecommendation(
                    license_id=str(lic.id),
                    provider_id=str(provider.id),
                    provider_name=provider.display_name,
                    external_user_id=lic.external_user_id,
                    license_type=lic.license_type,
                    employee_id=str(employee.id) if employee else None,
                    employee_name=employee.full_name if employee else None,
                    employee_email=employee.email if employee else None,
                    employee_status=employee.status if employee else None,
                    days_inactive=days_inactive,
                    last_activity_at=lic.last_activity_at,
                    monthly_cost=monthly_cost if monthly_cost > 0 else None,
                    yearly_savings=yearly_savings if yearly_savings > 0 else None,
                    recommendation_type=recommendation_type,
                    recommendation_reason=recommendation_reason,
                    priority=priority,
                    is_external_email=is_external,
                )
            )

        # Sort by priority (high first), then by cost (highest first)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(
            key=lambda r: (
                priority_order.get(r.priority, 3),
                -(r.monthly_cost or Decimal("0")),
            )
        )

        # Limit results
        recommendations = recommendations[:limit]

        # Count by priority
        high_count = sum(1 for r in recommendations if r.priority == "high")
        medium_count = sum(1 for r in recommendations if r.priority == "medium")
        low_count = sum(1 for r in recommendations if r.priority == "low")

        # Recalculate savings for limited results
        limited_monthly_savings = sum(r.monthly_cost or Decimal("0") for r in recommendations)

        return LicenseRecommendationsReport(
            total_recommendations=len(recommendations),
            high_priority_count=high_count,
            medium_priority_count=medium_count,
            low_priority_count=low_count,
            total_monthly_savings=limited_monthly_savings,
            total_yearly_savings=limited_monthly_savings * 12,
            recommendations=recommendations,
        )
