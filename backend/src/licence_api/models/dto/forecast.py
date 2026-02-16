"""Forecast DTOs for cost projection and scenario simulation."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ScenarioType(StrEnum):
    """Types of scenario adjustments."""

    ADD_EMPLOYEES = "add_employees"
    REMOVE_EMPLOYEES = "remove_employees"
    ADD_PROVIDER = "add_provider"
    REMOVE_PROVIDER = "remove_provider"
    CHANGE_SEATS = "change_seats"
    CHANGE_BILLING = "change_billing"


class ForecastDataPoint(BaseModel):
    """A single data point in a forecast time series."""

    month: date
    cost: Decimal
    is_historical: bool = True
    confidence_lower: Decimal | None = None
    confidence_upper: Decimal | None = None


class ProviderForecast(BaseModel):
    """Forecast breakdown for a single provider."""

    provider_id: UUID
    provider_name: str
    display_name: str
    current_cost: Decimal
    projected_cost: Decimal
    change_percent: float
    contract_end: date | None = None
    auto_renew: bool = True
    data_points: list[ForecastDataPoint] = Field(default_factory=list)


class DepartmentForecast(BaseModel):
    """Forecast breakdown for a single department."""

    department: str
    employee_count: int
    projected_employees: int
    current_cost: Decimal
    projected_cost: Decimal
    cost_per_employee: Decimal


class ForecastSummary(BaseModel):
    """Complete forecast response with summary and breakdowns."""

    current_monthly_cost: Decimal
    projected_monthly_cost: Decimal
    projected_annual_cost: Decimal
    change_percent: float
    forecast_months: int
    currency: str = "EUR"
    data_points: list[ForecastDataPoint] = Field(default_factory=list)
    by_provider: list[ProviderForecast] = Field(default_factory=list)
    by_department: list[DepartmentForecast] = Field(default_factory=list)


class AdjustmentRequest(BaseModel):
    """Request body for slider-based forecast adjustments."""

    forecast_months: int = Field(default=12, ge=1, le=24)
    history_months: int = Field(default=6, ge=1, le=24)
    price_adjustment_percent: float = Field(default=0.0, ge=-50.0, le=50.0)
    headcount_change: int = Field(default=0, ge=-50, le=50)
    provider_id: UUID | None = None


class ScenarioAdjustment(BaseModel):
    """A single adjustment in a what-if scenario."""

    type: ScenarioType
    provider_id: UUID | None = None
    provider_name: str | None = None
    department: str | None = None
    value: Decimal = Field(ge=0, le=1_000_000)
    effective_month: int = Field(ge=1, le=24, description="Month offset from now when adjustment takes effect")
    new_billing_cycle: str | None = Field(default=None, max_length=20)


class ScenarioRequest(BaseModel):
    """Request body for scenario simulation."""

    forecast_months: int = Field(default=12, ge=1, le=24)
    adjustments: list[ScenarioAdjustment] = Field(max_length=20)


class ScenarioResult(BaseModel):
    """Result of a scenario simulation."""

    baseline: list[ForecastDataPoint] = Field(default_factory=list)
    scenario: list[ForecastDataPoint] = Field(default_factory=list)
    baseline_total: Decimal
    scenario_total: Decimal
    difference: Decimal
    difference_percent: float
    currency: str = "EUR"
