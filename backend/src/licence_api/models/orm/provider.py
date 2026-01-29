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
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    credentials_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_method_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("payment_methods.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    licenses: Mapped[list["LicenseORM"]] = relationship(
        "LicenseORM", back_populates="provider", lazy="selectin"
    )
    files: Mapped[list["ProviderFileORM"]] = relationship(
        "ProviderFileORM", back_populates="provider", lazy="selectin", cascade="all, delete-orphan"
    )
    payment_method: Mapped["PaymentMethodORM | None"] = relationship(
        "PaymentMethodORM", lazy="selectin"
    )


# Import here to avoid circular import
from licence_api.models.orm.license import LicenseORM  # noqa: E402, F401
from licence_api.models.orm.provider_file import ProviderFileORM  # noqa: E402, F401
from licence_api.models.orm.payment_method import PaymentMethodORM  # noqa: E402, F401
