"""Exports router for CSV and Excel downloads."""

import re
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.security.auth import require_permission, Permissions
from licence_api.services.export_service import ExportService

router = APIRouter()

# Pattern for safe filename characters (alphanumeric, underscore, hyphen)
SAFE_FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")


def sanitize_filename_part(value: str, max_length: int = 30) -> str:
    """Sanitize a string for safe use in filenames.

    Removes any characters that are not alphanumeric, underscore, or hyphen.
    Truncates to max_length characters.
    """
    sanitized = SAFE_FILENAME_PATTERN.sub("_", value)
    return sanitized[:max_length]


def get_export_service(db: AsyncSession = Depends(get_db)) -> ExportService:
    """Get ExportService instance."""
    return ExportService(db)


@router.get("/licenses/csv")
async def export_licenses_csv(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_EXPORT))],
    export_service: Annotated[ExportService, Depends(get_export_service)],
    provider_id: UUID | None = Query(default=None, description="Filter by provider"),
    department: str | None = Query(default=None, max_length=100, description="Filter by department"),
    status: str | None = Query(default=None, max_length=50, description="Filter by status"),
) -> Response:
    """Export licenses to CSV format.

    Returns a downloadable CSV file with all license data.
    """
    csv_content = await export_service.export_licenses_csv(
        provider_id=provider_id,
        department=department,
        status=status,
    )

    filename = "licenses"
    if provider_id:
        filename += f"_provider_{str(provider_id)[:8]}"
    if department:
        filename += f"_{sanitize_filename_part(department)}"
    if status:
        filename += f"_{sanitize_filename_part(status)}"
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
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_EXPORT))],
    export_service: Annotated[ExportService, Depends(get_export_service)],
    start_date: date | None = Query(default=None, description="Start date"),
    end_date: date | None = Query(default=None, description="End date"),
) -> Response:
    """Export cost data to CSV format.

    Returns a downloadable CSV file with cost history.
    """
    csv_content = await export_service.export_costs_csv(
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
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_EXPORT))],
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> Response:
    """Export full report to Excel format.

    Returns a downloadable Excel file with multiple sheets:
    - Summary: Overview statistics
    - Licenses: All license data
    - Costs: Historical cost data
    """
    excel_content = await export_service.export_full_report_excel()

    filename = f"license_report_{date.today().isoformat()}.xlsx"

    return Response(
        content=excel_content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
