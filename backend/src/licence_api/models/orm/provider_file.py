"""Provider file ORM model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class ProviderFileORM(Base, UUIDMixin, TimestampMixin):
    """Provider file database model for storing contracts, invoices, etc."""

    __tablename__ = "provider_files"

    provider_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # Stored filename (UUID-based)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Original uploaded filename
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)  # MIME type
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Size in bytes
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # contract, invoice, other

    # Relationships
    provider: Mapped["ProviderORM"] = relationship("ProviderORM", back_populates="files")


# Import to avoid circular import
from licence_api.models.orm.provider import ProviderORM  # noqa: E402, F401
