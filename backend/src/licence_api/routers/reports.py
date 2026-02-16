"""Reports router."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from licence_api.dependencies import get_report_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.report import (
    CancelledLicensesReport,
    CostReportResponse,
    CostsByDepartmentReport,
    CostsByEmployeeReport,
    CostTrendReport,
    DuplicateAccountsReport,
    ExpiringContractsReport,
    ExpiringLicensesReport,
    ExternalUsersReport,
    InactiveLicenseReport,
    LicenseLifecycleOverview,
    LicenseRecommendationsReport,
    OffboardingReport,
    UtilizationReport,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import EXPENSIVE_READ_LIMIT, limiter
from licence_api.services.report_service import ReportService

router = APIRouter()


@router.get("/costs", response_model=CostReportResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_cost_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    start_date: date = Query(default=None, description="Report start date"),
    end_date: date = Query(default=None, description="Report end date"),
    department: str | None = Query(
        default=None, max_length=100, description="Filter by department"
    ),
) -> CostReportResponse:
    """Get cost report for specified date range.

    If dates are not specified, defaults to the last 3 months.
    """
    return await report_service.get_cost_report(start_date, end_date, department=department)


@router.get("/inactive", response_model=InactiveLicenseReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_inactive_license_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    days: int = Query(default=30, ge=1, le=365, description="Days of inactivity threshold"),
    department: str | None = Query(
        default=None, max_length=100, description="Filter by department"
    ),
) -> InactiveLicenseReport:
    """Get report of licenses without activity for specified days."""
    return await report_service.get_inactive_license_report(days, department=department)


@router.get("/offboarding", response_model=OffboardingReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_offboarding_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    department: str | None = Query(
        default=None, max_length=100, description="Filter by department"
    ),
) -> OffboardingReport:
    """Get report of offboarded employees with pending licenses."""
    return await report_service.get_offboarding_report(department=department)


@router.get("/external-users", response_model=ExternalUsersReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_external_users_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    department: str | None = Query(
        default=None, max_length=100, description="Filter by department"
    ),
) -> ExternalUsersReport:
    """Get report of licenses with external (non-company) email addresses."""
    return await report_service.get_external_users_report(department=department)


# ==================== QUICK WINS ====================


@router.get("/expiring-contracts", response_model=ExpiringContractsReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_expiring_contracts_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    days: int = Query(default=90, ge=1, le=365, description="Days ahead to check for expiry"),
) -> ExpiringContractsReport:
    """Get report of contracts expiring within specified days.

    Helps IT teams plan renewal negotiations and avoid auto-renewal surprises.
    """
    return await report_service.get_expiring_contracts(days_ahead=days)


@router.get("/utilization", response_model=UtilizationReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_utilization_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> UtilizationReport:
    """Get license utilization report comparing purchased vs assigned seats.

    Identifies over-provisioned licenses where you're paying for more seats
    than are actually being used. Response is cached for 5 minutes.
    """
    return await report_service.get_utilization_report_cached()


@router.get("/cost-trend", response_model=CostTrendReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_cost_trend_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    months: int = Query(default=6, ge=1, le=24, description="Number of months to show"),
) -> CostTrendReport:
    """Get cost trend over the last N months.

    Shows how license costs have changed over time, helping identify
    spending patterns and budget planning.
    """
    return await report_service.get_cost_trend(months=months)


@router.get("/duplicate-accounts", response_model=DuplicateAccountsReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_duplicate_accounts_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> DuplicateAccountsReport:
    """Get report of potential duplicate accounts across providers.

    Identifies accounts with the same email appearing multiple times
    within the same provider, which may indicate duplicate licenses.
    Response is cached for 5 minutes.
    """
    return await report_service.get_duplicate_accounts_cached()


# ==================== COST BREAKDOWN REPORTS ====================


@router.get("/costs-by-department", response_model=CostsByDepartmentReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_costs_by_department_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> CostsByDepartmentReport:
    """Get cost breakdown grouped by department.

    Shows license costs per department, employee count, and top providers.
    Helps identify which departments have the highest software costs.
    Response is cached for 5 minutes.
    """
    return await report_service.get_costs_by_department_cached()


@router.get("/costs-by-employee", response_model=CostsByEmployeeReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_costs_by_employee_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    department: str | None = Query(
        default=None, max_length=100, description="Filter by department"
    ),
    min_cost: float | None = Query(
        default=None, ge=0, le=1000000, description="Minimum monthly cost filter"
    ),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum employees to return"),
) -> CostsByEmployeeReport:
    """Get cost breakdown grouped by employee.

    Shows license costs per employee, sorted by highest cost first.
    Includes median and average statistics for benchmarking.
    Use min_cost to filter employees with costs above a threshold.
    """
    return await report_service.get_costs_by_employee(
        department=department,
        min_cost=min_cost,
        limit=limit,
    )


# ==================== LICENSE LIFECYCLE REPORTS ====================


@router.get("/expiring-licenses", response_model=ExpiringLicensesReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_expiring_licenses_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    days: int = Query(default=90, ge=1, le=365, description="Days ahead to check for expiry"),
) -> ExpiringLicensesReport:
    """Get report of licenses expiring within specified days.

    Shows licenses that will expire soon, along with counts for different time windows
    and licenses that are marked as needing reorder.
    """
    return await report_service.get_expiring_licenses_report(days_ahead=days)


@router.get("/cancelled-licenses", response_model=CancelledLicensesReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_cancelled_licenses_report(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> CancelledLicensesReport:
    """Get report of cancelled licenses.

    Shows licenses that have been cancelled, including those with pending
    effective dates and those already effective.
    """
    return await report_service.get_cancelled_licenses_report()


@router.get("/lifecycle-overview", response_model=LicenseLifecycleOverview)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_lifecycle_overview(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> LicenseLifecycleOverview:
    """Get comprehensive license lifecycle overview.

    Combines counts of active, expiring, expired, cancelled, and needs-reorder
    licenses along with detailed lists of expiring and cancelled licenses.
    """
    return await report_service.get_license_lifecycle_overview()


# ==================== LICENSE RECOMMENDATIONS ====================


@router.get("/recommendations", response_model=LicenseRecommendationsReport)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_license_recommendations(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    min_days_inactive: int = Query(
        default=60, ge=30, le=365, description="Minimum days of inactivity to consider"
    ),
    department: str | None = Query(
        default=None, max_length=100, description="Filter by department"
    ),
    provider_id: str | None = Query(
        default=None, max_length=36, description="Filter by provider UUID"
    ),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum recommendations to return"),
) -> LicenseRecommendationsReport:
    """Get license optimization recommendations based on usage patterns.

    Analyzes inactive licenses and generates actionable recommendations:
    - **Cancel**: For licenses inactive >90 days with no assigned employee
    - **Reassign**: For licenses inactive >60 days but assigned to active employee
    - **Review**: For other potentially wasteful licenses

    Recommendations are prioritized by:
    - Employee status (offboarded employees are highest priority)
    - Days of inactivity
    - Monthly cost (higher cost = higher priority)
    - External email addresses

    Returns estimated monthly and yearly savings if recommendations are implemented.
    """
    return await report_service.get_license_recommendations(
        min_days_inactive=min_days_inactive,
        department=department,
        provider_id=provider_id,
        limit=limit,
    )
