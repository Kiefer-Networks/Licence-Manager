"""Reports router."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
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
    OffboardingReport,
    UtilizationReport,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.services.report_service import ReportService

router = APIRouter()


def get_report_service(db: AsyncSession = Depends(get_db)) -> ReportService:
    """Get ReportService instance."""
    return ReportService(db)


@router.get("/costs", response_model=CostReportResponse)
async def get_cost_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    start_date: date = Query(default=None, description="Report start date"),
    end_date: date = Query(default=None, description="Report end date"),
    department: str | None = Query(default=None, max_length=100, description="Filter by department"),
) -> CostReportResponse:
    """Get cost report for specified date range.

    If dates are not specified, defaults to the last 3 months.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=90)

    return await report_service.get_cost_report(start_date, end_date, department=department)


@router.get("/inactive", response_model=InactiveLicenseReport)
async def get_inactive_license_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    days: int = Query(default=30, ge=1, le=365, description="Days of inactivity threshold"),
    department: str | None = Query(default=None, max_length=100, description="Filter by department"),
) -> InactiveLicenseReport:
    """Get report of licenses without activity for specified days."""
    return await report_service.get_inactive_license_report(days, department=department)


@router.get("/offboarding", response_model=OffboardingReport)
async def get_offboarding_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    department: str | None = Query(default=None, max_length=100, description="Filter by department"),
) -> OffboardingReport:
    """Get report of offboarded employees with pending licenses."""
    return await report_service.get_offboarding_report(department=department)


@router.get("/external-users", response_model=ExternalUsersReport)
async def get_external_users_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    department: str | None = Query(default=None, max_length=100, description="Filter by department"),
) -> ExternalUsersReport:
    """Get report of licenses with external (non-company) email addresses."""
    return await report_service.get_external_users_report(department=department)


# ==================== QUICK WINS ====================


@router.get("/expiring-contracts", response_model=ExpiringContractsReport)
async def get_expiring_contracts_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    days: int = Query(default=90, ge=1, le=365, description="Days ahead to check for expiry"),
) -> ExpiringContractsReport:
    """Get report of contracts expiring within specified days.

    Helps IT teams plan renewal negotiations and avoid auto-renewal surprises.
    """
    return await report_service.get_expiring_contracts(days_ahead=days)


@router.get("/utilization", response_model=UtilizationReport)
async def get_utilization_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> UtilizationReport:
    """Get license utilization report comparing purchased vs assigned seats.

    Identifies over-provisioned licenses where you're paying for more seats
    than are actually being used.
    """
    return await report_service.get_utilization_report()


@router.get("/cost-trend", response_model=CostTrendReport)
async def get_cost_trend_report(
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
async def get_duplicate_accounts_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> DuplicateAccountsReport:
    """Get report of potential duplicate accounts across providers.

    Identifies accounts with the same email appearing multiple times
    within the same provider, which may indicate duplicate licenses.
    """
    return await report_service.get_duplicate_accounts()


# ==================== COST BREAKDOWN REPORTS ====================


@router.get("/costs-by-department", response_model=CostsByDepartmentReport)
async def get_costs_by_department_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> CostsByDepartmentReport:
    """Get cost breakdown grouped by department.

    Shows license costs per department, employee count, and top providers.
    Helps identify which departments have the highest software costs.
    """
    return await report_service.get_costs_by_department()


@router.get("/costs-by-employee", response_model=CostsByEmployeeReport)
async def get_costs_by_employee_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    department: str | None = Query(default=None, max_length=100, description="Filter by department"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum employees to return"),
) -> CostsByEmployeeReport:
    """Get cost breakdown grouped by employee.

    Shows license costs per employee, sorted by highest cost first.
    Includes median and average statistics for benchmarking.
    """
    return await report_service.get_costs_by_employee(department=department, limit=limit)


# ==================== LICENSE LIFECYCLE REPORTS ====================


@router.get("/expiring-licenses", response_model=ExpiringLicensesReport)
async def get_expiring_licenses_report(
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
async def get_cancelled_licenses_report(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> CancelledLicensesReport:
    """Get report of cancelled licenses.

    Shows licenses that have been cancelled, including those with pending
    effective dates and those already effective.
    """
    return await report_service.get_cancelled_licenses_report()


@router.get("/lifecycle-overview", response_model=LicenseLifecycleOverview)
async def get_lifecycle_overview(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> LicenseLifecycleOverview:
    """Get comprehensive license lifecycle overview.

    Combines counts of active, expiring, expired, cancelled, and needs-reorder
    licenses along with detailed lists of expiring and cancelled licenses.
    """
    return await report_service.get_license_lifecycle_overview()
