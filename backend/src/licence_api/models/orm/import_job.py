"""Import Job ORM model for tracking license imports."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class ImportJobORM(Base, UUIDMixin, TimestampMixin):
    """Import Job database model for tracking license imports."""

    __tablename__ = "import_jobs"

    provider_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    column_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    options: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    provider: Mapped["ProviderORM"] = relationship("ProviderORM")
    creator: Mapped["AdminUserORM | None"] = relationship("AdminUserORM")

    __table_args__ = (
        Index("idx_import_jobs_provider", "provider_id"),
        Index("idx_import_jobs_status", "status"),
        Index("idx_import_jobs_created_by", "created_by"),
        Index("idx_import_jobs_created_at", "created_at"),
    )


# Import to avoid circular import issues
from licence_api.models.orm.admin_user import AdminUserORM  # noqa: E402, F401
from licence_api.models.orm.provider import ProviderORM  # noqa: E402, F401
