"""Exports router for CSV and Excel downloads."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.security.auth import get_current_user
from licence_api.services.export_service import ExportService

router = APIRouter()


@router.get("/licenses/csv")
async def export_licenses_csv(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_id: UUID | None = Query(default=None, description="Filter by provider"),
    department: str | None = Query(default=None, description="Filter by department"),
    status: str | None = Query(default=None, description="Filter by status"),
) -> Response:
    """Export licenses to CSV format.

    Returns a downloadable CSV file with all license data.
    """
    service = ExportService(db)
    csv_content = await service.export_licenses_csv(
        provider_id=provider_id,
        department=department,
        status=status,
    )

    filename = "licenses"
    if provider_id:
        filename += f"_provider_{str(provider_id)[:8]}"
    if department:
        filename += f"_{department.replace(' ', '_')}"
    if status:
        filename += f"_{status}"
    filename += f"_{date.today().isoformat()}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get("/costs/csv")
async def export_costs_csv(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: date | None = Query(default=None, description="Start date"),
    end_date: date | None = Query(default=None, description="End date"),
) -> Response:
    """Export cost data to CSV format.

    Returns a downloadable CSV file with cost history.
    """
    service = ExportService(db)
    csv_content = await service.export_costs_csv(
        start_date=start_date,
        end_date=end_date,
    )

    filename = f"costs_{date.today().isoformat()}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get("/full-report/excel")
async def export_full_report_excel(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Export full report to Excel format.

    Returns a downloadable Excel file with multiple sheets:
    - Summary: Overview statistics
    - Licenses: All license data
    - Costs: Historical cost data
    """
    service = ExportService(db)
    excel_content = await service.export_full_report_excel()

    filename = f"license_report_{date.today().isoformat()}.xlsx"

    return Response(
        content=excel_content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
