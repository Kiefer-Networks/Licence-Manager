"""Forecast service for cost projections and scenario simulations."""

import math
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.dto.forecast import (
    AdjustmentRequest,
    DepartmentForecast,
    ForecastDataPoint,
    ForecastSummary,
    ProviderForecast,
    ScenarioAdjustment,
    ScenarioRequest,
    ScenarioResult,
    ScenarioType,
)
from licence_api.models.orm.cost_snapshot import CostSnapshotORM
from licence_api.models.orm.license_package import LicensePackageORM
from licence_api.repositories.forecast_repository import ForecastRepository

# Z-score for 80% confidence interval
_Z_SCORE_80 = 1.28


def _linear_regression(
    x: list[float], y: list[float]
) -> tuple[float, float]:
    """Compute least-squares linear regression (y = slope*x + intercept).

    Args:
        x: Independent variable values
        y: Dependent variable values

    Returns:
        Tuple of (slope, intercept)
    """
    n = len(x)
    if n == 0:
        return 0.0, 0.0

    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi * xi for xi in x)

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return 0.0, sum_y / n if n > 0 else 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    return slope, intercept


def _residual_std(
    x: list[float], y: list[float], slope: float, intercept: float
) -> float:
    """Compute residual standard deviation."""
    n = len(x)
    if n <= 2:
        return 0.0

    residuals = [(yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y)]
    return math.sqrt(sum(residuals) / (n - 2))


def _prediction_interval(
    x_vals: list[float], x_pred: float, std_resid: float, n: int
) -> float:
    """Compute prediction interval half-width for a given x_pred."""
    if n <= 2 or std_resid == 0:
        return 0.0

    x_mean = sum(x_vals) / n
    ss_x = sum((xi - x_mean) ** 2 for xi in x_vals)
    if ss_x == 0:
        return 0.0

    width = std_resid * _Z_SCORE_80 * math.sqrt(1 + 1 / n + (x_pred - x_mean) ** 2 / ss_x)
    return width


def _add_months(base_date: date, months: int) -> date:
    """Add months to a date, returning the first of the target month."""
    total_months = base_date.month + months
    year = base_date.year + (total_months - 1) // 12
    month = (total_months - 1) % 12 + 1
    return date(year, month, 1)


class ForecastService:
    """Service for generating cost forecasts and running scenario simulations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.repo = ForecastRepository(session)

    async def _ensure_snapshots(self) -> None:
        """Create cost snapshots from live data if none exist."""
        from licence_api.services.cost_snapshot_service import CostSnapshotService

        service = CostSnapshotService(self.session)
        await service.ensure_current_snapshot_exists()

    async def get_forecast(
        self,
        months: int = 12,
        provider_id: UUID | None = None,
        department: str | None = None,
        history_months: int = 6,
    ) -> ForecastSummary:
        """Generate a cost forecast.

        Args:
            months: Number of months to project forward
            provider_id: Optional filter to forecast a single provider
            department: Optional filter for department-level analysis
            history_months: Number of months of history to include (min 3 for regression)

        Returns:
            ForecastSummary with data points and breakdowns
        """
        # Fetch enough history for regression (at least 3), but display only requested
        fetch_months = max(history_months, 3)
        history = await self.repo.get_cost_history(
            months=fetch_months, provider_id=provider_id
        )

        # Fallback: if no snapshots exist, create them on-the-fly from live data
        if not history and not provider_id:
            await self._ensure_snapshots()
            history = await self.repo.get_cost_history(
                months=fetch_months, provider_id=provider_id
            )

        # Build total forecast data points
        data_points = self._build_forecast(history, months)

        # Current and projected costs
        current_cost = Decimal(str(history[-1].total_cost)) if history else Decimal("0")
        projected_cost = data_points[-1].cost if data_points else current_cost
        projected_annual = projected_cost * 12
        change_pct = (
            float((projected_cost - current_cost) / current_cost * 100)
            if current_cost > 0
            else 0.0
        )

        # Provider breakdowns
        by_provider: list[ProviderForecast] = []
        if not provider_id:
            by_provider = await self._build_provider_forecasts(months)

        # Department breakdowns
        by_department: list[DepartmentForecast] = []
        if not provider_id:
            by_department = await self._build_department_forecasts(months, department)

        return ForecastSummary(
            current_monthly_cost=current_cost,
            projected_monthly_cost=projected_cost,
            projected_annual_cost=projected_annual,
            change_percent=round(change_pct, 1),
            forecast_months=months,
            data_points=data_points,
            by_provider=by_provider,
            by_department=by_department,
        )

    async def simulate_scenario(
        self,
        request: ScenarioRequest,
    ) -> ScenarioResult:
        """Run a what-if scenario simulation.

        Args:
            request: Scenario parameters with adjustments

        Returns:
            ScenarioResult comparing baseline and adjusted projections
        """
        history = await self.repo.get_cost_history(months=24)
        baseline_points = self._build_forecast(history, request.forecast_months)

        # Start with baseline projected values
        scenario_points = [
            ForecastDataPoint(
                month=dp.month,
                cost=dp.cost,
                is_historical=dp.is_historical,
                confidence_lower=dp.confidence_lower,
                confidence_upper=dp.confidence_upper,
            )
            for dp in baseline_points
        ]

        # Pre-fetch all data needed by adjustments to avoid N+1 queries
        dept_costs = await self.repo.get_department_costs()
        dept_headcount = await self.repo.get_active_count_by_department()
        total_emps = await self.repo.get_active_employee_count()
        latest_history = await self.repo.get_cost_history(months=1)
        latest_total_cost = (
            latest_history[-1].total_cost if latest_history else Decimal("0")
        )

        # Batch-fetch provider data for all referenced providers
        provider_ids = {
            adj.provider_id for adj in request.adjustments if adj.provider_id
        }
        provider_costs: dict[UUID, Decimal] = {}
        for pid in provider_ids:
            provider_costs[pid] = await self.repo.get_provider_current_cost(pid)

        all_packages = await self.repo.get_provider_packages()
        pkgs_by_provider: dict[UUID, list[LicensePackageORM]] = {}
        for pkg in all_packages:
            pkgs_by_provider.setdefault(pkg.provider_id, []).append(pkg)

        # Apply each adjustment using pre-fetched data (no more async calls)
        for adj in request.adjustments:
            self._apply_adjustment(
                scenario_points,
                adj,
                dept_costs=dept_costs,
                dept_headcount=dept_headcount,
                total_emps=total_emps,
                latest_total_cost=latest_total_cost,
                provider_costs=provider_costs,
                provider_packages=pkgs_by_provider,
            )

        baseline_total = sum(
            dp.cost for dp in baseline_points if not dp.is_historical
        )
        scenario_total = sum(
            dp.cost for dp in scenario_points if not dp.is_historical
        )
        difference = scenario_total - baseline_total
        diff_pct = (
            float(difference / baseline_total * 100) if baseline_total > 0 else 0.0
        )

        return ScenarioResult(
            baseline=baseline_points,
            scenario=scenario_points,
            baseline_total=baseline_total,
            scenario_total=scenario_total,
            difference=difference,
            difference_percent=round(diff_pct, 1),
        )

    async def get_adjusted_forecast(
        self,
        request: AdjustmentRequest,
    ) -> ForecastSummary:
        """Generate a forecast with slider-based adjustments applied.

        Applies price and headcount factors only to projected data points,
        leaving historical data untouched.

        Args:
            request: Adjustment parameters (price %, headcount change)

        Returns:
            ForecastSummary with adjusted projections
        """
        baseline = await self.get_forecast(
            months=request.forecast_months,
            provider_id=request.provider_id,
            history_months=request.history_months,
        )

        price_factor = 1.0 + (request.price_adjustment_percent / 100.0)
        # Headcount factor: use provider license count or total employees as basis
        if request.provider_id:
            base_count = await self.repo.get_provider_license_count(request.provider_id)
        else:
            base_count = await self.repo.get_active_employee_count()
        if base_count > 0 and request.headcount_change != 0:
            headcount_factor = 1.0 + (request.headcount_change / base_count)
        else:
            headcount_factor = 1.0

        combined_factor = Decimal(str(round(price_factor * headcount_factor, 6)))

        # Apply factor to projected data points only
        adjusted_points: list[ForecastDataPoint] = []
        for dp in baseline.data_points:
            if dp.is_historical:
                adjusted_points.append(dp)
            else:
                adjusted_cost = max(Decimal("0"), round(dp.cost * combined_factor, 2))
                adjusted_lower = (
                    max(Decimal("0"), round(dp.confidence_lower * combined_factor, 2))
                    if dp.confidence_lower is not None
                    else None
                )
                adjusted_upper = (
                    round(dp.confidence_upper * combined_factor, 2)
                    if dp.confidence_upper is not None
                    else None
                )
                adjusted_points.append(
                    ForecastDataPoint(
                        month=dp.month,
                        cost=adjusted_cost,
                        is_historical=False,
                        confidence_lower=adjusted_lower,
                        confidence_upper=adjusted_upper,
                    )
                )

        # Recalculate summary values
        projected_cost = adjusted_points[-1].cost if adjusted_points else Decimal("0")
        projected_annual = projected_cost * 12
        current_cost = baseline.current_monthly_cost
        change_pct = (
            float((projected_cost - current_cost) / current_cost * 100)
            if current_cost > 0
            else 0.0
        )

        # Adjust provider forecasts
        adjusted_providers: list[ProviderForecast] = []
        for pf in baseline.by_provider:
            adj_points: list[ForecastDataPoint] = []
            for dp in pf.data_points:
                if dp.is_historical:
                    adj_points.append(dp)
                else:
                    adj_points.append(
                        ForecastDataPoint(
                            month=dp.month,
                            cost=max(Decimal("0"), round(dp.cost * combined_factor, 2)),
                            is_historical=False,
                            confidence_lower=(
                                max(Decimal("0"), round(dp.confidence_lower * combined_factor, 2))
                                if dp.confidence_lower is not None
                                else None
                            ),
                            confidence_upper=(
                                round(dp.confidence_upper * combined_factor, 2)
                                if dp.confidence_upper is not None
                                else None
                            ),
                        )
                    )
            adj_projected = adj_points[-1].cost if adj_points else pf.projected_cost
            adj_change = (
                float((adj_projected - pf.current_cost) / pf.current_cost * 100)
                if pf.current_cost > 0
                else 0.0
            )
            adjusted_providers.append(
                ProviderForecast(
                    provider_id=pf.provider_id,
                    provider_name=pf.provider_name,
                    display_name=pf.display_name,
                    current_cost=pf.current_cost,
                    projected_cost=adj_projected,
                    change_percent=round(adj_change, 1),
                    contract_end=pf.contract_end,
                    auto_renew=pf.auto_renew,
                    data_points=adj_points,
                )
            )

        return ForecastSummary(
            current_monthly_cost=current_cost,
            projected_monthly_cost=projected_cost,
            projected_annual_cost=projected_annual,
            change_percent=round(change_pct, 1),
            forecast_months=request.forecast_months,
            data_points=adjusted_points,
            by_provider=adjusted_providers,
            by_department=baseline.by_department,
        )

    def _build_forecast(
        self,
        history: list[CostSnapshotORM],
        forecast_months: int,
    ) -> list[ForecastDataPoint]:
        """Build forecast data points from historical data.

        Uses linear regression with >= 3 data points, weighted moving
        average with 1-2 points, or flat projection with 0 points.
        """
        data_points: list[ForecastDataPoint] = []

        # Historical data points
        for snap in history:
            data_points.append(
                ForecastDataPoint(
                    month=snap.snapshot_date,
                    cost=snap.total_cost,
                    is_historical=True,
                )
            )

        if not history:
            # No data - return empty projection
            today = date.today()
            base = date(today.year, today.month, 1)
            for i in range(1, forecast_months + 1):
                future_date = _add_months(base, i)
                data_points.append(
                    ForecastDataPoint(
                        month=future_date,
                        cost=Decimal("0"),
                        is_historical=False,
                        confidence_lower=Decimal("0"),
                        confidence_upper=Decimal("0"),
                    )
                )
            return data_points

        n = len(history)
        costs = [float(snap.total_cost) for snap in history]
        x_vals = list(range(n))

        if n >= 3:
            # Linear regression
            slope, intercept = _linear_regression(x_vals, costs)
            std = _residual_std(x_vals, costs, slope, intercept)
        else:
            # Weighted moving average fallback
            if n == 2:
                avg = costs[0] * 0.3 + costs[1] * 0.7
            else:
                avg = costs[0]
            slope = 0.0
            intercept = avg
            std = 0.0

        # Generate future points
        last_date = history[-1].snapshot_date
        for i in range(1, forecast_months + 1):
            future_date = _add_months(last_date, i)
            x_pred = n - 1 + i  # Continue from last data point

            predicted = slope * x_pred + intercept
            predicted = max(predicted, 0)  # Cost can't be negative

            interval = _prediction_interval(x_vals, x_pred, std, n)
            lower = max(predicted - interval, 0)
            upper = predicted + interval

            data_points.append(
                ForecastDataPoint(
                    month=future_date,
                    cost=Decimal(str(round(predicted, 2))),
                    is_historical=False,
                    confidence_lower=Decimal(str(round(lower, 2))),
                    confidence_upper=Decimal(str(round(upper, 2))),
                )
            )

        return data_points

    async def _build_provider_forecasts(
        self,
        months: int,
    ) -> list[ProviderForecast]:
        """Build per-provider forecast breakdowns."""
        providers = await self.repo.get_active_providers()
        histories = await self.repo.get_all_provider_cost_histories(months=24)
        packages_list = await self.repo.get_provider_packages()

        # Index packages by provider
        packages_by_provider: dict[UUID, list[LicensePackageORM]] = {}
        for pkg in packages_list:
            packages_by_provider.setdefault(pkg.provider_id, []).append(pkg)

        results: list[ProviderForecast] = []
        for provider in providers:
            history = histories.get(provider.id, [])
            current_cost = (
                Decimal(str(history[-1].total_cost)) if history else Decimal("0")
            )

            # Provider forecast data points
            provider_points = self._build_forecast(history, months)

            # Apply contract awareness
            pkgs = packages_by_provider.get(provider.id, [])
            contract_end = None
            auto_renew = True
            for pkg in pkgs:
                if pkg.contract_end:
                    if contract_end is None or pkg.contract_end < contract_end:
                        contract_end = pkg.contract_end
                    if not pkg.auto_renew:
                        auto_renew = False

            # If contract ends and doesn't auto-renew, zero out after end date
            if contract_end and not auto_renew:
                for dp in provider_points:
                    if not dp.is_historical and dp.month > contract_end:
                        dp.cost = Decimal("0")
                        dp.confidence_lower = Decimal("0")
                        dp.confidence_upper = Decimal("0")

            projected_cost = provider_points[-1].cost if provider_points else current_cost
            change_pct = (
                float((projected_cost - current_cost) / current_cost * 100)
                if current_cost > 0
                else 0.0
            )

            results.append(
                ProviderForecast(
                    provider_id=provider.id,
                    provider_name=provider.name,
                    display_name=provider.display_name,
                    current_cost=current_cost,
                    projected_cost=projected_cost,
                    change_percent=round(change_pct, 1),
                    contract_end=contract_end,
                    auto_renew=auto_renew,
                    data_points=provider_points,
                )
            )

        # Sort by current cost descending
        results.sort(key=lambda r: r.current_cost, reverse=True)
        return results

    async def _build_department_forecasts(
        self,
        months: int,
        department: str | None = None,
    ) -> list[DepartmentForecast]:
        """Build per-department forecast breakdowns."""
        dept_costs = await self.repo.get_department_costs()
        dept_headcount = await self.repo.get_active_count_by_department()

        # Get headcount trend for employee projection
        headcount_history = await self.repo.get_employee_headcount(months=12)

        # Simple headcount projection using trend
        if len(headcount_history) >= 3:
            x = list(range(len(headcount_history)))
            y = [float(count) for _, count in headcount_history]
            slope, intercept = _linear_regression(x, y)
            projected_total = max(0, slope * (len(headcount_history) - 1 + months) + intercept)
        else:
            projected_total = sum(dept_headcount.values()) if dept_headcount else 0
            slope = 0

        total_current = sum(dept_headcount.values()) if dept_headcount else 1

        results: list[DepartmentForecast] = []
        all_depts = set(dept_headcount.keys()) | set(dept_costs.keys())
        for dept in all_depts:
            if department and dept != department:
                continue

            current_cost = dept_costs.get(dept, Decimal("0"))
            emp_count = dept_headcount.get(dept, 0)
            cost_per_emp = (
                current_cost / emp_count if emp_count > 0 else Decimal("0")
            )

            # Project department headcount proportionally
            if total_current > 0:
                dept_ratio = emp_count / total_current
                projected_emps = max(0, round(projected_total * dept_ratio))
            else:
                projected_emps = emp_count

            projected_cost = cost_per_emp * projected_emps

            results.append(
                DepartmentForecast(
                    department=dept,
                    employee_count=emp_count,
                    projected_employees=projected_emps,
                    current_cost=current_cost,
                    projected_cost=round(projected_cost, 2),
                    cost_per_employee=round(cost_per_emp, 2),
                )
            )

        results.sort(key=lambda r: r.current_cost, reverse=True)
        return results

    def _apply_adjustment(
        self,
        scenario_points: list[ForecastDataPoint],
        adj: ScenarioAdjustment,
        *,
        dept_costs: dict[str, Decimal],
        dept_headcount: dict[str, int],
        total_emps: int,
        latest_total_cost: Decimal,
        provider_costs: dict[UUID, Decimal],
        provider_packages: dict[UUID, list[LicensePackageORM]],
    ) -> None:
        """Apply a single scenario adjustment to projected data points.

        Uses pre-fetched data to avoid N+1 queries.
        """
        # Find the first projected month index
        projected_indices = [
            i for i, dp in enumerate(scenario_points) if not dp.is_historical
        ]
        if not projected_indices:
            return

        first_proj_idx = projected_indices[0]
        # effective_month is 1-based offset from the first projected month
        start_idx = first_proj_idx + adj.effective_month - 1

        if adj.type == ScenarioType.ADD_EMPLOYEES:
            delta = self._get_employee_cost_delta(
                adj.department, int(adj.value),
                dept_costs=dept_costs,
                dept_headcount=dept_headcount,
                total_emps=total_emps,
                latest_total_cost=latest_total_cost,
            )
            for i in range(start_idx, len(scenario_points)):
                if not scenario_points[i].is_historical:
                    scenario_points[i].cost += delta

        elif adj.type == ScenarioType.REMOVE_EMPLOYEES:
            delta = self._get_employee_cost_delta(
                adj.department, int(adj.value),
                dept_costs=dept_costs,
                dept_headcount=dept_headcount,
                total_emps=total_emps,
                latest_total_cost=latest_total_cost,
            )
            for i in range(start_idx, len(scenario_points)):
                if not scenario_points[i].is_historical:
                    scenario_points[i].cost = max(
                        Decimal("0"), scenario_points[i].cost - delta
                    )

        elif adj.type == ScenarioType.ADD_PROVIDER:
            monthly_cost = adj.value
            for i in range(start_idx, len(scenario_points)):
                if not scenario_points[i].is_historical:
                    scenario_points[i].cost += monthly_cost

        elif adj.type == ScenarioType.REMOVE_PROVIDER:
            if adj.provider_id:
                provider_cost = provider_costs.get(adj.provider_id, Decimal("0"))
                for i in range(start_idx, len(scenario_points)):
                    if not scenario_points[i].is_historical:
                        scenario_points[i].cost = max(
                            Decimal("0"),
                            scenario_points[i].cost - provider_cost,
                        )

        elif adj.type == ScenarioType.CHANGE_SEATS:
            if adj.provider_id:
                packages = provider_packages.get(adj.provider_id, [])
                if packages:
                    # Use average cost per seat across packages (Decimal precision)
                    seat_costs = [
                        p.cost_per_seat for p in packages if p.cost_per_seat
                    ]
                    avg_cost = (
                        sum(seat_costs, Decimal("0")) / len(seat_costs)
                        if seat_costs
                        else Decimal("0")
                    )
                    current_seats = sum(p.total_seats for p in packages)
                    new_seats = int(adj.value)
                    seat_delta = new_seats - current_seats
                    cost_change = round(Decimal(seat_delta) * avg_cost, 2)
                    for i in range(start_idx, len(scenario_points)):
                        if not scenario_points[i].is_historical:
                            scenario_points[i].cost = max(
                                Decimal("0"),
                                scenario_points[i].cost + cost_change,
                            )

        elif adj.type == ScenarioType.CHANGE_BILLING:
            if adj.provider_id:
                provider_cost = provider_costs.get(adj.provider_id, Decimal("0"))
                # Apply discount for yearly billing (~17.5% avg)
                new_cycle = (adj.new_billing_cycle or "").lower()
                if new_cycle == "yearly":
                    discount = Decimal("0.175")
                    cost_change = -(provider_cost * discount)
                elif new_cycle == "monthly":
                    # Remove yearly discount
                    discount = Decimal("0.175")
                    cost_change = provider_cost * discount
                else:
                    cost_change = Decimal("0")

                for i in range(start_idx, len(scenario_points)):
                    if not scenario_points[i].is_historical:
                        scenario_points[i].cost = max(
                            Decimal("0"),
                            scenario_points[i].cost + cost_change,
                        )

    def _get_employee_cost_delta(
        self,
        department: str | None,
        count: int,
        *,
        dept_costs: dict[str, Decimal],
        dept_headcount: dict[str, int],
        total_emps: int,
        latest_total_cost: Decimal,
    ) -> Decimal:
        """Calculate cost impact of adding/removing employees.

        Uses pre-fetched data to avoid redundant queries.
        """
        if department:
            dept_cost = dept_costs.get(department, Decimal("0"))
            dept_count = dept_headcount.get(department, 0)
            cost_per_emp = dept_cost / dept_count if dept_count > 0 else Decimal("0")
        else:
            cost_per_emp = (
                latest_total_cost / total_emps if total_emps > 0 else Decimal("0")
            )

        return round(cost_per_emp * count, 2)
