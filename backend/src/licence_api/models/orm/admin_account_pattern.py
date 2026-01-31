"""Admin Account Pattern ORM model."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class AdminAccountPatternORM(Base, UUIDMixin, TimestampMixin):
    """Admin Account Pattern database model for detecting admin accounts."""

    __tablename__ = "admin_account_patterns"

    email_pattern: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    owner: Mapped["EmployeeORM | None"] = relationship(
        "EmployeeORM",
        foreign_keys=[owner_id],
        lazy="selectin",
    )
    creator: Mapped["AdminUserORM | None"] = relationship(
        "AdminUserORM",
        foreign_keys=[created_by],
        lazy="selectin",
    )


# Import here to avoid circular import
from licence_api.models.orm.admin_user import AdminUserORM  # noqa: E402, F401
from licence_api.models.orm.employee import EmployeeORM  # noqa: E402, F401
