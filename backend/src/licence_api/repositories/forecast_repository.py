"""Forecast repository for aggregating data needed for cost projections."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from licence_api.models.orm.cost_snapshot import CostSnapshotORM
from licence_api.models.orm.employee import EmployeeORM
from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.license_package import LicensePackageORM
from licence_api.models.orm.provider import ProviderORM
from licence_api.repositories.cost_snapshot_repository import CostSnapshotRepository
from licence_api.repositories.employee_repository import EmployeeRepository


class ForecastRepository:
    """Aggregates data from multiple repositories for forecast calculations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self.session = session
        self.cost_snapshot_repo = CostSnapshotRepository(session)
        self.employee_repo = EmployeeRepository(session)

    async def get_cost_history(
        self,
        months: int = 24,
        provider_id: UUID | None = None,
    ) -> list[CostSnapshotORM]:
        """Get historical cost snapshots for forecasting."""
        return await self.cost_snapshot_repo.get_trend(months=months, provider_id=provider_id)

    async def get_all_provider_cost_histories(
        self,
        months: int = 24,
    ) -> dict[UUID, list[CostSnapshotORM]]:
        """Get cost histories grouped by provider."""
        result = await self.session.execute(
            select(CostSnapshotORM)
            .where(CostSnapshotORM.provider_id.isnot(None))
            .order_by(CostSnapshotORM.snapshot_date.asc())
        )
        snapshots = result.scalars().all()

        histories: dict[UUID, list[CostSnapshotORM]] = {}
        for snap in snapshots:
            if snap.provider_id not in histories:
                histories[snap.provider_id] = []
            histories[snap.provider_id].append(snap)

        # Limit to last N months per provider
        for pid in histories:
            histories[pid] = histories[pid][-months:]

        return histories

    async def get_active_providers(self) -> list[ProviderORM]:
        """Get all enabled providers."""
        result = await self.session.execute(
            select(ProviderORM).where(ProviderORM.enabled.is_(True))
        )
        return list(result.scalars().all())

    async def get_provider_packages(
        self,
        provider_id: UUID | None = None,
    ) -> list[LicensePackageORM]:
        """Get active license packages, optionally filtered by provider."""
        query = select(LicensePackageORM).where(
            LicensePackageORM.status == "active"
        )
        if provider_id:
            query = query.where(LicensePackageORM.provider_id == provider_id)

        query = query.options(selectinload(LicensePackageORM.provider))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_employee_headcount(
        self,
        months: int = 12,
        department: str | None = None,
    ) -> list[tuple[date, int]]:
        """Get monthly headcount history."""
        return await self.employee_repo.get_monthly_headcount(
            months=months, department=department
        )

    async def get_department_costs(self) -> dict[str, Decimal]:
        """Get current monthly cost per department.

        Distributes provider-level package costs across departments
        proportionally by active license count. This avoids the broken
        license_type JOIN (License.license_type is nullable, causing
        NULL == NULL → FALSE in SQL).
        """
        # Step 1: Get total monthly cost per provider from packages
        provider_costs = await self.get_provider_costs_from_packages()
        if not provider_costs:
            return {}

        # Step 2: Count active licenses per provider (for cost-per-license calc)
        license_count_result = await self.session.execute(
            select(
                LicenseORM.provider_id,
                func.count(LicenseORM.id),
            )
            .where(LicenseORM.status == "active")
            .group_by(LicenseORM.provider_id)
        )
        licenses_per_provider = {pid: count for pid, count in license_count_result.all()}

        cost_per_license: dict[UUID, Decimal] = {}
        for pid, total_cost in provider_costs.items():
            license_count = licenses_per_provider.get(pid, 0)
            if license_count > 0:
                cost_per_license[pid] = round(total_cost / license_count, 4)

        # Step 3: Count licenses per department+provider, then multiply by cost_per_license
        dept_license_result = await self.session.execute(
            select(
                EmployeeORM.department,
                LicenseORM.provider_id,
                func.count(LicenseORM.id),
            )
            .join(LicenseORM, LicenseORM.employee_id == EmployeeORM.id)
            .where(
                EmployeeORM.status == "active",
                LicenseORM.status == "active",
            )
            .group_by(EmployeeORM.department, LicenseORM.provider_id)
        )

        dept_costs: dict[str, Decimal] = {}
        for dept, provider_id, lcount in dept_license_result.all():
            dept_key = dept or "-"
            cpl = cost_per_license.get(provider_id, Decimal("0"))
            dept_costs[dept_key] = dept_costs.get(dept_key, Decimal("0")) + round(
                cpl * lcount, 2
            )

        return dept_costs

    async def get_active_employee_count(
        self,
        department: str | None = None,
    ) -> int:
        """Get current active employee count."""
        query = (
            select(func.count())
            .select_from(EmployeeORM)
            .where(EmployeeORM.status == "active")
        )
        if department:
            query = query.where(EmployeeORM.department == department)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_active_count_by_department(self) -> dict[str, int]:
        """Get active employee counts by department."""
        return await self.employee_repo.get_active_count_by_department()

    async def get_provider_by_id(self, provider_id: UUID) -> ProviderORM | None:
        """Get a single provider by ID."""
        result = await self.session.execute(
            select(ProviderORM).where(ProviderORM.id == provider_id)
        )
        return result.scalar_one_or_none()

    async def get_provider_costs_from_packages(self) -> dict[UUID, Decimal]:
        """Calculate monthly costs per provider from active license packages.

        Normalizes billing_cycle: yearly costs are divided by 12,
        quarterly by 3, monthly stays as-is.

        Returns:
            Dict mapping provider_id to monthly cost.
        """
        result = await self.session.execute(
            select(LicensePackageORM).where(
                LicensePackageORM.status == "active",
                LicensePackageORM.cost_per_seat.isnot(None),
            )
        )
        packages = result.scalars().all()

        costs: dict[UUID, Decimal] = {}
        for pkg in packages:
            raw_cost = pkg.cost_per_seat * pkg.total_seats
            cycle = (pkg.billing_cycle or "monthly").lower()
            if cycle == "yearly":
                monthly = raw_cost / 12
            elif cycle == "quarterly":
                monthly = raw_cost / 3
            else:
                monthly = raw_cost
            costs[pkg.provider_id] = costs.get(pkg.provider_id, Decimal("0")) + round(monthly, 2)

        return costs

    async def get_provider_current_cost(self, provider_id: UUID) -> Decimal:
        """Get current monthly cost for a provider from latest snapshot.

        Falls back to package-based calculation if snapshot shows zero cost.
        """
        snapshot = await self.cost_snapshot_repo.get_latest(provider_id=provider_id)
        cost = snapshot.total_cost if snapshot else Decimal("0")
        if cost == Decimal("0"):
            package_costs = await self.get_provider_costs_from_packages()
            cost = package_costs.get(provider_id, Decimal("0"))
        return cost
