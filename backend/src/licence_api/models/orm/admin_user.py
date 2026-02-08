"""Admin user ORM model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class AdminUserORM(Base, UUIDMixin, TimestampMixin):
    """Admin user database model with Google OAuth support."""

    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Authentication fields (Google OAuth only)
    auth_provider: Mapped[str] = mapped_column(String(50), default="google", nullable=False)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Login tracking
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Locale preferences (language: ISO 639-1 codes like en, de)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="en")
    date_format: Mapped[str | None] = mapped_column(String(20), nullable=True, default="DD.MM.YYYY")
    number_format: Mapped[str | None] = mapped_column(String(20), nullable=True, default="de-DE")
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True, default="EUR")

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
    notification_preferences: Mapped[list["UserNotificationPreferenceORM"]] = relationship(
        "UserNotificationPreferenceORM",
        back_populates="user",
        cascade="all, delete-orphan",
    )
