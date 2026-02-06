"""User notification preference ORM model."""

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class UserNotificationPreferenceORM(Base, UUIDMixin, TimestampMixin):
    """User notification preference database model.

    Stores per-user notification preferences for different event types.
    Users can choose which notifications they want to receive and optionally
    specify a custom Slack channel or DM preference.
    """

    __tablename__ = "user_notification_preferences"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Notification delivery preferences
    slack_dm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    slack_channel: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["AdminUserORM"] = relationship(
        "AdminUserORM", back_populates="notification_preferences"
    )

    __table_args__ = (UniqueConstraint("user_id", "event_type", name="uq_user_notification_pref"),)


# Import here to avoid circular import
from licence_api.models.orm.admin_user import AdminUserORM  # noqa: E402, F401
