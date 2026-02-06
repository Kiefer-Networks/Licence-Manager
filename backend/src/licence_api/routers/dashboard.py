"""Dashboard router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.dashboard import DashboardResponse
from licence_api.security.auth import Permissions, require_permission
from licence_api.services.cache_service import get_cache_service
from licence_api.services.report_service import ReportService
from licence_api.utils.validation import sanitize_department

router = APIRouter()


def get_report_service(db: AsyncSession = Depends(get_db)) -> ReportService:
    """Get ReportService instance."""
    return ReportService(db)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
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

    # Try to get from cache
    cache = await get_cache_service()
    cached = await cache.get_dashboard(department=department)
    if cached:
        return DashboardResponse(**cached)

    # Fetch from database
    result = await report_service.get_dashboard(department=department)

    # Cache the result
    await cache.set_dashboard(result, department=department)

    return result
