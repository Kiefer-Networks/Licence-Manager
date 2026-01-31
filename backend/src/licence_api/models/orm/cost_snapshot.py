"""Cost snapshot ORM model for historical cost tracking."""

from datetime import date
from decimal import Decimal
from uuid import UUID as PyUUID

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class CostSnapshotORM(Base, UUIDMixin, TimestampMixin):
    """Model for storing monthly cost snapshots."""

    __tablename__ = "cost_snapshots"

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    provider_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    license_count: Mapped[int] = mapped_column(Integer, nullable=False)
    active_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unassigned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    provider = relationship("ProviderORM", back_populates="cost_snapshots")

    __table_args__ = (
        UniqueConstraint("snapshot_date", "provider_id", name="uq_cost_snapshot_date_provider"),
    )

    def __repr__(self) -> str:
        provider_info = f"provider={self.provider_id}" if self.provider_id else "total"
        return f"<CostSnapshot {self.snapshot_date} {provider_info} {self.total_cost} {self.currency}>"
