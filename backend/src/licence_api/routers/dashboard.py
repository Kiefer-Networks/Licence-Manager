"""Dashboard router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.dashboard import DashboardResponse
from licence_api.security.auth import get_current_user
from licence_api.services.report_service import ReportService

router = APIRouter()


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    department: str | None = Query(default=None, description="Filter by department"),
) -> DashboardResponse:
    """Get dashboard overview data.

    Returns summary statistics, provider status, recent alerts,
    and unassigned licenses.
    """
    service = ReportService(db)
    return await service.get_dashboard(department=department)
