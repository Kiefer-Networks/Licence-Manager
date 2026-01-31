"""Provider ORM model."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class ProviderORM(Base, UUIDMixin, TimestampMixin):
    """Provider database model."""

    __tablename__ = "providers"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    credentials_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_method_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("payment_methods.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships - use lazy="select" for collections to avoid N+1 queries
    # Load explicitly with selectinload() when needed
    licenses: Mapped[list["LicenseORM"]] = relationship(
        "LicenseORM", back_populates="provider", lazy="select", cascade="all, delete-orphan"
    )
    files: Mapped[list["ProviderFileORM"]] = relationship(
        "ProviderFileORM", back_populates="provider", lazy="select", cascade="all, delete-orphan"
    )
    payment_method: Mapped["PaymentMethodORM | None"] = relationship(
        "PaymentMethodORM", lazy="joined"
    )
    license_packages: Mapped[list["LicensePackageORM"]] = relationship(
        "LicensePackageORM", back_populates="provider", lazy="select", cascade="all, delete-orphan"
    )
    organization_licenses: Mapped[list["OrganizationLicenseORM"]] = relationship(
        "OrganizationLicenseORM", back_populates="provider", lazy="select", cascade="all, delete-orphan"
    )
    cost_snapshots: Mapped[list["CostSnapshotORM"]] = relationship(
        "CostSnapshotORM", back_populates="provider", lazy="select", cascade="all, delete-orphan"
    )


# Import here to avoid circular import
from licence_api.models.orm.license import LicenseORM  # noqa: E402, F401
from licence_api.models.orm.provider_file import ProviderFileORM  # noqa: E402, F401
from licence_api.models.orm.payment_method import PaymentMethodORM  # noqa: E402, F401
from licence_api.models.orm.license_package import LicensePackageORM  # noqa: E402, F401
from licence_api.models.orm.organization_license import OrganizationLicenseORM  # noqa: E402, F401
from licence_api.models.orm.cost_snapshot import CostSnapshotORM  # noqa: E402, F401
