"""Organization license ORM model."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class OrgLicenseStatus:
    """Organization license status constants."""

    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OrganizationLicenseORM(Base, UUIDMixin, TimestampMixin):
    """Organization-wide license database model.

    For licenses that belong to the organization, not individual users.
    Examples: SharePoint storage, Power Platform capacity, etc.
    """

    __tablename__ = "organization_licenses"

    provider_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    license_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int | None] = mapped_column(nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    monthly_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    billing_cycle: Mapped[str | None] = mapped_column(String(20), nullable=True)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Expiration tracking
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

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
    provider: Mapped["ProviderORM"] = relationship(
        "ProviderORM", back_populates="organization_licenses"
    )
    canceller: Mapped["AdminUserORM | None"] = relationship(
        "AdminUserORM", foreign_keys=[cancelled_by]
    )

    __table_args__ = (Index("idx_org_licenses_provider", "provider_id"),)


# Import here to avoid circular import
from licence_api.models.orm.admin_user import AdminUserORM  # noqa: E402, F401
from licence_api.models.orm.provider import ProviderORM  # noqa: E402, F401
