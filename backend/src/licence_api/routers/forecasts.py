"""Forecasts router for cost projections and scenario simulations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from licence_api.dependencies import get_forecast_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.forecast import AdjustmentRequest, ForecastSummary, ScenarioRequest, ScenarioResult
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import EXPENSIVE_READ_LIMIT, SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.forecast_service import ForecastService
from licence_api.utils.validation import sanitize_department

router = APIRouter()


@router.get("/", response_model=ForecastSummary)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_forecast(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    forecast_service: Annotated[ForecastService, Depends(get_forecast_service)],
    months: int = Query(default=12, ge=1, le=24, description="Number of months to forecast"),
    history_months: int = Query(default=6, ge=1, le=24, description="Number of months of history to include"),
    provider_id: UUID | None = Query(default=None, description="Filter by provider UUID"),
    department: str | None = Query(
        default=None, max_length=100, description="Filter by department"
    ),
) -> ForecastSummary:
    """Get baseline cost forecast.

    Projects future license costs using linear regression on historical
    cost snapshots. Includes confidence intervals and breakdowns by
    provider and department.
    """
    sanitized_department = sanitize_department(department)

    return await forecast_service.get_forecast(
        months=months,
        provider_id=provider_id,
        department=sanitized_department,
        history_months=history_months,
    )


@router.get("/adjust", response_model=ForecastSummary)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def adjust_forecast(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    forecast_service: Annotated[ForecastService, Depends(get_forecast_service)],
    forecast_months: int = Query(default=12, ge=1, le=24),
    history_months: int = Query(default=6, ge=1, le=24),
    price_adjustment_percent: float = Query(default=0.0, ge=-50.0, le=50.0),
    headcount_change: int = Query(default=0, ge=-5000, le=5000),
    provider_id: UUID | None = Query(default=None),
) -> ForecastSummary:
    """Get forecast with slider-based adjustments applied.

    Accepts price adjustment percentage and headcount change,
    returns forecast with adjusted projections.
    """
    return await forecast_service.get_adjusted_forecast(
        request=AdjustmentRequest(
            forecast_months=forecast_months,
            history_months=history_months,
            price_adjustment_percent=price_adjustment_percent,
            headcount_change=headcount_change,
            provider_id=provider_id,
        )
    )


@router.post("/scenarios", response_model=ScenarioResult)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def simulate_scenario(
    request: Request,
    body: ScenarioRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.REPORTS_VIEW))],
    forecast_service: Annotated[ForecastService, Depends(get_forecast_service)],
) -> ScenarioResult:
    """Run a what-if scenario simulation.

    Accepts a set of adjustments (add/remove employees, providers,
    change seats/billing) and returns baseline vs scenario comparison.
    """
    return await forecast_service.simulate_scenario(request=body)
