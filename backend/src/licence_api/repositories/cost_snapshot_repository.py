"""Cost snapshot repository for historical cost tracking."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.cost_snapshot import CostSnapshotORM
from licence_api.repositories.base import BaseRepository


class CostSnapshotRepository(BaseRepository[CostSnapshotORM]):
    """Repository for cost snapshot operations."""

    model = CostSnapshotORM

    async def get_by_date_and_provider(
        self,
        snapshot_date: date,
        provider_id: UUID | None = None,
    ) -> CostSnapshotORM | None:
        """Get snapshot for a specific date and provider.

        Args:
            snapshot_date: The snapshot date
            provider_id: Provider UUID or None for total

        Returns:
            CostSnapshotORM or None if not found
        """
        if provider_id is None:
            result = await self.session.execute(
                select(CostSnapshotORM).where(
                    and_(
                        CostSnapshotORM.snapshot_date == snapshot_date,
                        CostSnapshotORM.provider_id.is_(None),
                    )
                )
            )
        else:
            result = await self.session.execute(
                select(CostSnapshotORM).where(
                    and_(
                        CostSnapshotORM.snapshot_date == snapshot_date,
                        CostSnapshotORM.provider_id == provider_id,
                    )
                )
            )
        return result.scalar_one_or_none()

    async def get_trend(
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
        if provider_id is None:
            result = await self.session.execute(
                select(CostSnapshotORM)
                .where(CostSnapshotORM.provider_id.is_(None))
                .order_by(desc(CostSnapshotORM.snapshot_date))
                .limit(months)
            )
        else:
            result = await self.session.execute(
                select(CostSnapshotORM)
                .where(CostSnapshotORM.provider_id == provider_id)
                .order_by(desc(CostSnapshotORM.snapshot_date))
                .limit(months)
            )
        # Return in ascending order (oldest first)
        return list(reversed(list(result.scalars().all())))

    async def get_range(
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
        conditions = [
            CostSnapshotORM.snapshot_date >= start_date,
            CostSnapshotORM.snapshot_date <= end_date,
        ]

        if provider_id is None:
            conditions.append(CostSnapshotORM.provider_id.is_(None))
        else:
            conditions.append(CostSnapshotORM.provider_id == provider_id)

        result = await self.session.execute(
            select(CostSnapshotORM)
            .where(and_(*conditions))
            .order_by(CostSnapshotORM.snapshot_date)
        )
        return list(result.scalars().all())

    async def create_or_update(
        self,
        snapshot_date: date,
        total_cost: Decimal,
        license_count: int,
        active_count: int = 0,
        unassigned_count: int = 0,
        provider_id: UUID | None = None,
        currency: str = "EUR",
        breakdown: dict | None = None,
    ) -> CostSnapshotORM:
        """Create or update a snapshot for a specific date and provider.

        Args:
            snapshot_date: The snapshot date
            total_cost: Total cost
            license_count: Number of licenses
            active_count: Number of active licenses
            unassigned_count: Number of unassigned licenses
            provider_id: Provider UUID or None for total
            currency: Currency code
            breakdown: Additional breakdown data

        Returns:
            Created or updated snapshot
        """
        existing = await self.get_by_date_and_provider(snapshot_date, provider_id)

        if existing:
            existing.total_cost = total_cost
            existing.license_count = license_count
            existing.active_count = active_count
            existing.unassigned_count = unassigned_count
            existing.currency = currency
            existing.breakdown = breakdown
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        return await self.create(
            snapshot_date=snapshot_date,
            provider_id=provider_id,
            total_cost=total_cost,
            license_count=license_count,
            active_count=active_count,
            unassigned_count=unassigned_count,
            currency=currency,
            breakdown=breakdown,
        )

    async def get_latest(
        self,
        provider_id: UUID | None = None,
    ) -> CostSnapshotORM | None:
        """Get the most recent snapshot.

        Args:
            provider_id: Filter by provider or None for totals

        Returns:
            Most recent snapshot or None
        """
        if provider_id is None:
            result = await self.session.execute(
                select(CostSnapshotORM)
                .where(CostSnapshotORM.provider_id.is_(None))
                .order_by(desc(CostSnapshotORM.snapshot_date))
                .limit(1)
            )
        else:
            result = await self.session.execute(
                select(CostSnapshotORM)
                .where(CostSnapshotORM.provider_id == provider_id)
                .order_by(desc(CostSnapshotORM.snapshot_date))
                .limit(1)
            )
        return result.scalar_one_or_none()
