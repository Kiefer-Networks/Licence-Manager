"""License ORM model."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class LicenseORM(Base, UUIDMixin, TimestampMixin):
    """License database model."""

    __tablename__ = "licenses"

    provider_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    license_type: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    monthly_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, default=dict, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Service account fields
    is_service_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    service_account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_account_owner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    provider: Mapped["ProviderORM"] = relationship("ProviderORM", back_populates="licenses")
    employee: Mapped["EmployeeORM | None"] = relationship(
        "EmployeeORM", back_populates="licenses", foreign_keys=[employee_id]
    )
    service_account_owner: Mapped["EmployeeORM | None"] = relationship(
        "EmployeeORM", foreign_keys=[service_account_owner_id]
    )

    __table_args__ = (
        UniqueConstraint("provider_id", "external_user_id", name="uq_license_provider_external"),
        Index("idx_licenses_provider", "provider_id"),
        Index("idx_licenses_employee", "employee_id"),
        Index("idx_licenses_status", "status"),
        Index("idx_licenses_last_activity", "last_activity_at"),
    )


# Import here to avoid circular import
from licence_api.models.orm.employee import EmployeeORM  # noqa: E402, F401
from licence_api.models.orm.provider import ProviderORM  # noqa: E402, F401
