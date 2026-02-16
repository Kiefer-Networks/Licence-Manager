"""Dashboard router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from licence_api.dependencies import get_report_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.dashboard import DashboardResponse
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import EXPENSIVE_READ_LIMIT, limiter
from licence_api.services.report_service import ReportService
from licence_api.utils.validation import sanitize_department

router = APIRouter()


@router.get("", response_model=DashboardResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_dashboard(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.DASHBOARD_VIEW))],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    department: str | None = Query(default=None, description="Filter by department"),
) -> DashboardResponse:
    """Get dashboard overview data.

    Returns summary statistics, provider status, recent alerts,
    and unassigned licenses.

    Response is cached for 5 minutes to improve performance.
    """
    # Sanitize input
    department = sanitize_department(department)

    return await report_service.get_dashboard_cached(department=department)
