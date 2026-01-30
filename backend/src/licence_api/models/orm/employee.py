"""Employee ORM model."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class EmployeeORM(Base, UUIDMixin, TimestampMixin):
    """Employee database model."""

    __tablename__ = "employees"

    hibob_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    licenses: Mapped[list["LicenseORM"]] = relationship(
        "LicenseORM",
        back_populates="employee",
        lazy="selectin",
        foreign_keys="[LicenseORM.employee_id]",
    )

    __table_args__ = (
        Index("idx_employees_email", "email"),
        Index("idx_employees_status", "status"),
    )


# Import here to avoid circular import
from licence_api.models.orm.license import LicenseORM  # noqa: E402, F401
