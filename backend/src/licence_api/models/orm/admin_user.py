"""Admin user ORM model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class AdminUserORM(Base, UUIDMixin, TimestampMixin):
    """Admin user database model with local auth support."""

    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Authentication fields
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)

    # Security fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Password management
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    require_password_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Login tracking
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    roles: Mapped[list["RoleORM"]] = relationship(
        "RoleORM",
        secondary="user_roles",
        back_populates="users",
        primaryjoin="AdminUserORM.id == user_roles.c.user_id",
        secondaryjoin="RoleORM.id == user_roles.c.role_id",
    )
    refresh_tokens: Mapped[list["RefreshTokenORM"]] = relationship(
        "RefreshTokenORM",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_history: Mapped[list["PasswordHistoryORM"]] = relationship(
        "PasswordHistoryORM",
        back_populates="user",
        cascade="all, delete-orphan",
    )
