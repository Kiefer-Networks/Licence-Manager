"""Notification rule ORM model."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from licence_api.models.orm.base import Base, TimestampMixin, UUIDMixin


class NotificationRuleORM(Base, UUIDMixin, TimestampMixin):
    """Notification rule database model."""

    __tablename__ = "notification_rules"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    slack_channel: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    template: Mapped[str | None] = mapped_column(Text, nullable=True)
