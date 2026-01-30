"""Report service for generating license reports."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.dto.report import (
    CostReportResponse,
    InactiveLicenseReport,
    InactiveLicenseEntry,
    OffboardingReport,
    OffboardedEmployee,
    MonthlyCost,
    ExternalUsersReport,
    ExternalUserLicense,
)
from licence_api.models.dto.dashboard import (
    DashboardResponse,
    ProviderSummary,
    RecentOffboarding,
    UnassignedLicense,
)
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.settings_repository import SettingsRepository
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
            employee_licenses = await self.license_repo.get_licenses_with_providers_for_employees(employee_ids)

            for employee in recent_offboarded:
                licenses_with_providers = employee_licenses.get(employee.id, [])
                if licenses_with_providers:
                    # Get unique provider names from the batch result
                    provider_names = list({provider.display_name for _, provider in licenses_with_providers})

                    recent_offboardings.append(
                        RecentOffboarding(
                            employee_id=str(employee.id),
                            employee_name=employee.full_name,
                            employee_email=employee.email,
                            termination_date=datetime.combine(
                                employee.termination_date, datetime.min.time()
                            ) if employee.termination_date else None,
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

        for lic, provider, _ in results:
            # Skip HRIS providers (they don't have licenses)
            if provider.name == "hibob":
                continue
            name = provider.display_name
            cost = lic.monthly_cost or Decimal("0")
            provider_costs[name] = provider_costs.get(name, Decimal("0")) + cost
            provider_counts[name] = provider_counts.get(name, 0) + 1

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

        return CostReportResponse(
            start_date=start_date,
            end_date=end_date,
            total_cost=total_cost,
            monthly_costs=monthly_costs,
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
                days_inactive = (datetime.now(timezone.utc) - lic.last_activity_at).days
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
            employee_licenses = await self.license_repo.get_licenses_with_providers_for_employees(employee_ids)

            for employee in offboarded:
                licenses_with_providers = employee_licenses.get(employee.id, [])
                if licenses_with_providers:
                    pending_licenses = []
                    for lic, provider in licenses_with_providers:
                        pending_licenses.append({
                            "provider": provider.display_name,
                            "type": lic.license_type or "Unknown",
                            "external_id": lic.external_user_id,
                        })

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
