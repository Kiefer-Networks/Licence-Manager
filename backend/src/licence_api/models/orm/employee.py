"""Employee ORM model."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
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
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="hibob")

    # Manager relationship - stores email from HRIS, resolved to ID after sync
    manager_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships - use lazy="select" for collections to avoid N+1 queries
    # Load explicitly with selectinload() when needed
    licenses: Mapped[list["LicenseORM"]] = relationship(
        "LicenseORM",
        back_populates="employee",
        lazy="select",
        foreign_keys="[LicenseORM.employee_id]",
    )

    # Manager relationship (self-referential)
    manager: Mapped["EmployeeORM | None"] = relationship(
        "EmployeeORM",
        remote_side="EmployeeORM.id",
        foreign_keys=[manager_id],
        lazy="select",
    )

    # External accounts (provider usernames linked to this employee)
    external_accounts: Mapped[list["EmployeeExternalAccountORM"]] = relationship(
        "EmployeeExternalAccountORM",
        back_populates="employee",
        lazy="select",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_employees_email", "email"),
        Index("idx_employees_status", "status"),
        Index("idx_employees_manager_id", "manager_id"),
        Index("idx_employees_source", "source"),
    )


# Import here to avoid circular import
from licence_api.models.orm.employee_external_account import (
    EmployeeExternalAccountORM,  # noqa: E402, F401
)
from licence_api.models.orm.license import LicenseORM  # noqa: E402, F401
