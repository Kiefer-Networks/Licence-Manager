"""Permission ORM model."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class PermissionORM(Base, UUIDMixin, TimestampMixin):
    """Permission database model."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Relationships
    roles: Mapped[list["RoleORM"]] = relationship(
        "RoleORM",
        secondary="role_permissions",
        back_populates="permissions",
    )
