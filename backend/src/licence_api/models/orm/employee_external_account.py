"""Employee external account ORM model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class EmployeeExternalAccountORM(Base, UUIDMixin, TimestampMixin):
    """Maps external provider usernames to employees.

    This allows matching licenses to employees when providers don't return
    email addresses (e.g., Hugging Face without SCIM).
    """

    __tablename__ = "employee_external_accounts"

    employee_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Provider type (e.g., "huggingface", "github", etc.)
    provider_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # The username in the external system
    external_username: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional: The user's ID in the external system (for more robust matching)
    external_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Optional: Display name from the external system
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # When this link was created
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Who created this link (admin user ID)
    linked_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )

    # Relationships
    employee: Mapped["EmployeeORM"] = relationship(
        "EmployeeORM",
        back_populates="external_accounts",
        lazy="select",
    )

    __table_args__ = (
        # Each provider username can only be linked to one employee
        UniqueConstraint(
            "provider_type",
            "external_username",
            name="uq_employee_external_accounts_provider_username",
        ),
        Index("ix_employee_external_accounts_employee_id", "employee_id"),
        Index("ix_employee_external_accounts_provider_type", "provider_type"),
        Index("ix_employee_external_accounts_external_username", "external_username"),
    )


# Import here to avoid circular import
from licence_api.models.orm.employee import EmployeeORM  # noqa: E402, F401
