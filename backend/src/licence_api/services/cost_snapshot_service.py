"""Cost snapshot service for creating and managing cost snapshots."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.cost_snapshot import CostSnapshotORM
from licence_api.repositories.cost_snapshot_repository import CostSnapshotRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository


class CostSnapshotService:
    """Service for cost snapshot operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.snapshot_repo = CostSnapshotRepository(session)
        self.license_repo = LicenseRepository(session)
        self.provider_repo = ProviderRepository(session)

    async def create_monthly_snapshot(
        self,
        snapshot_date: date | None = None,
    ) -> list[CostSnapshotORM]:
        """Create monthly cost snapshots for all providers and total.

        Creates snapshots for the first day of the month.

        Args:
            snapshot_date: Optional date (defaults to first of current month)

        Returns:
            List of created snapshots
        """
        if snapshot_date is None:
            snapshot_date = date.today().replace(day=1)

        snapshots = []

        # Get all providers
        providers = await self.provider_repo.get_all(limit=1000)

        # Track totals
        total_cost = Decimal("0")
        total_license_count = 0
        total_active_count = 0
        total_unassigned_count = 0
        provider_breakdown = {}

        for provider in providers:
            # Skip HRIS providers (hibob)
            if provider.name == "hibob":
                continue

            # Get license statistics for this provider
            stats = await self.license_repo.get_statistics(provider_id=provider.id)

            provider_cost = stats.get("total_monthly_cost", Decimal("0"))
            provider_license_count = stats.get("total", 0)
            provider_active = stats.get("by_status", {}).get("active", 0)
            provider_unassigned = stats.get("unassigned", 0)

            # Create provider snapshot
            snapshot = await self.snapshot_repo.create_or_update(
                snapshot_date=snapshot_date,
                provider_id=provider.id,
                total_cost=provider_cost,
                license_count=provider_license_count,
                active_count=provider_active,
                unassigned_count=provider_unassigned,
                currency="EUR",
            )
            snapshots.append(snapshot)

            # Add to totals
            total_cost += provider_cost
            total_license_count += provider_license_count
            total_active_count += provider_active
            total_unassigned_count += provider_unassigned

            # Add to breakdown
            provider_breakdown[str(provider.id)] = {
                "name": provider.display_name,
                "cost": str(provider_cost),
                "licenses": provider_license_count,
            }

        # Create total snapshot (provider_id = None)
        total_snapshot = await self.snapshot_repo.create_or_update(
            snapshot_date=snapshot_date,
            provider_id=None,
            total_cost=total_cost,
            license_count=total_license_count,
            active_count=total_active_count,
            unassigned_count=total_unassigned_count,
            currency="EUR",
            breakdown={"providers": provider_breakdown},
        )
        snapshots.append(total_snapshot)

        await self.session.commit()
        return snapshots

    async def get_cost_trend(
        self,
        months: int = 6,
        provider_id: UUID | None = None,
    ) -> list[CostSnapshotORM]:
        """Get cost trend for the last N months.

        Args:
            months: Number of months to retrieve
            provider_id: Filter by provider or None for totals

        Returns:
            List of snapshots ordered by date ascending
        """
        return await self.snapshot_repo.get_trend(months=months, provider_id=provider_id)

    async def get_cost_range(
        self,
        start_date: date,
        end_date: date,
        provider_id: UUID | None = None,
    ) -> list[CostSnapshotORM]:
        """Get snapshots within a date range.

        Args:
            start_date: Start date
            end_date: End date
            provider_id: Filter by provider or None for totals

        Returns:
            List of snapshots within the range
        """
        return await self.snapshot_repo.get_range(
            start_date=start_date,
            end_date=end_date,
            provider_id=provider_id,
        )

    async def ensure_current_snapshot_exists(self) -> CostSnapshotORM | None:
        """Ensure a snapshot exists for the current month.

        Creates one if it doesn't exist.

        Returns:
            The current month's total snapshot
        """
        current_month = date.today().replace(day=1)
        existing = await self.snapshot_repo.get_by_date_and_provider(
            snapshot_date=current_month,
            provider_id=None,
        )

        if existing is None:
            snapshots = await self.create_monthly_snapshot(snapshot_date=current_month)
            # Return the total snapshot
            for snapshot in snapshots:
                if snapshot.provider_id is None:
                    return snapshot
            return None

        return existing
