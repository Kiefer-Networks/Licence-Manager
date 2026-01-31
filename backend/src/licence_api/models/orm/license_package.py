"""License package ORM model."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class PackageStatus:
    """Package status constants."""

    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class LicensePackageORM(Base, UUIDMixin, TimestampMixin):
    """License package database model for tracking purchased seat counts."""

    __tablename__ = "license_packages"

    provider_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    license_type: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_seats: Mapped[int] = mapped_column(nullable=False)
    cost_per_seat: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    billing_cycle: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    contract_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cancellation tracking
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    needs_reorder: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    # Relationships
    provider: Mapped["ProviderORM"] = relationship("ProviderORM", back_populates="license_packages")
    canceller: Mapped["AdminUserORM | None"] = relationship("AdminUserORM", foreign_keys=[cancelled_by])

    __table_args__ = (
        UniqueConstraint("provider_id", "license_type", name="uq_package_provider_type"),
        Index("idx_license_packages_provider", "provider_id"),
    )


# Import here to avoid circular import
from licence_api.models.orm.provider import ProviderORM  # noqa: E402, F401
from licence_api.models.orm.admin_user import AdminUserORM  # noqa: E402, F401
