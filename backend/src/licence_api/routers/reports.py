"""Reports router."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.report import (
    CostReportResponse,
    InactiveLicenseReport,
    OffboardingReport,
    ExternalUsersReport,
)
from licence_api.security.auth import get_current_user
from licence_api.services.report_service import ReportService

router = APIRouter()


@router.get("/costs", response_model=CostReportResponse)
async def get_cost_report(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: date = Query(default=None, description="Report start date"),
    end_date: date = Query(default=None, description="Report end date"),
    department: str | None = Query(default=None, description="Filter by department"),
) -> CostReportResponse:
    """Get cost report for specified date range.

    If dates are not specified, defaults to the last 3 months.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=90)

    service = ReportService(db)
    return await service.get_cost_report(start_date, end_date, department=department)


@router.get("/inactive", response_model=InactiveLicenseReport)
async def get_inactive_license_report(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365, description="Days of inactivity threshold"),
    department: str | None = Query(default=None, description="Filter by department"),
) -> InactiveLicenseReport:
    """Get report of licenses without activity for specified days."""
    service = ReportService(db)
    return await service.get_inactive_license_report(days, department=department)


@router.get("/offboarding", response_model=OffboardingReport)
async def get_offboarding_report(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    department: str | None = Query(default=None, description="Filter by department"),
) -> OffboardingReport:
    """Get report of offboarded employees with pending licenses."""
    service = ReportService(db)
    return await service.get_offboarding_report(department=department)


@router.get("/external-users", response_model=ExternalUsersReport)
async def get_external_users_report(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    department: str | None = Query(default=None, description="Filter by department"),
) -> ExternalUsersReport:
    """Get report of licenses with external (non-company) email addresses."""
    service = ReportService(db)
    return await service.get_external_users_report(department=department)
