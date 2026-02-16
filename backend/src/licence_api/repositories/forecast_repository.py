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
        """Get current monthly cost per department based on license assignments.

        Sums cost_per_seat for all active licenses grouped by employee department.
        """
        result = await self.session.execute(
            select(
                EmployeeORM.department,
                func.coalesce(func.sum(LicensePackageORM.cost_per_seat), 0),
            )
            .join(LicenseORM, LicenseORM.employee_id == EmployeeORM.id)
            .join(ProviderORM, ProviderORM.id == LicenseORM.provider_id)
            .outerjoin(
                LicensePackageORM,
                (LicensePackageORM.provider_id == LicenseORM.provider_id)
                & (LicensePackageORM.license_type == LicenseORM.license_type)
                & (LicensePackageORM.status == "active"),
            )
            .where(
                EmployeeORM.status == "active",
                EmployeeORM.department.isnot(None),
                LicenseORM.status == "active",
            )
            .group_by(EmployeeORM.department)
        )
        return {dept: Decimal(str(cost)) for dept, cost in result.all()}

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

    async def get_provider_current_cost(self, provider_id: UUID) -> Decimal:
        """Get current monthly cost for a provider from latest snapshot."""
        snapshot = await self.cost_snapshot_repo.get_latest(provider_id=provider_id)
        return snapshot.total_cost if snapshot else Decimal("0")
