"""Role ORM model."""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class RoleORM(Base, UUIDMixin, TimestampMixin):
    """Role database model."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    permissions: Mapped[list["PermissionORM"]] = relationship(
        "PermissionORM",
        secondary="role_permissions",
        back_populates="roles",
    )
    users: Mapped[list["AdminUserORM"]] = relationship(
        "AdminUserORM",
        secondary="user_roles",
        back_populates="roles",
        primaryjoin="RoleORM.id == user_roles.c.role_id",
        secondaryjoin="AdminUserORM.id == user_roles.c.user_id",
    )
